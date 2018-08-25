import os
import argparse
import logging
import sys
from collections import defaultdict
from itertools import groupby
from operator import itemgetter
from time import sleep
import humanfriendly as hf
from requests import ReadTimeout

from . import db

log = logging.getLogger('plexiglas')


def process_opts(opts):
    import keyring

    init_logging(opts)

    if opts.username:
        log.debug('Username provided, updating in keyring')
        keyring.set_password('plexiglas', 'myplex_login', opts.username)
    else:
        log.debug('No username in args')
        opts.username = keyring.get_password('plexiglas', 'myplex_login')

        if not opts.username:
            log.debug('No username in keyring')
            opts.username = input('Please provide MyPlex login: ').strip()

            if opts.username:
                keyring.set_password('plexiglas', 'myplex_login', opts.username)

    if not opts.username:
        log.debug('No username')
        print('MyPlex login is required')
        exit(1)

    if opts.password:
        keyring.set_password('plexiglas', opts.username, opts.password)
    else:
        opts.password = keyring.get_password('plexiglas', opts.username)

    if not opts.password:
        import getpass
        opts.password = getpass.getpass('Enter the plex.tv password for %s: ' % opts.username)
        keyring.set_password('plexiglas', opts.username, opts.password)

    opts.destination = os.path.expanduser(opts.destination)

    if not os.access(opts.destination, os.W_OK):
        try:
            os.makedirs(opts.destination, exist_ok=True)
        except OSError:
            print('Directory "%s" should be writable' % opts.destination)
            exit(1)

    os.chdir(opts.destination)

    if opts.log_file_max_size:
        opts.log_file_max_size = hf.parse_size(opts.log_file_max_size, binary=True)

    if opts.limit_disk_usage:
        if '%' in opts.limit_disk_usage:
            tokens = hf.tokenize(opts.limit_disk_usage)
            if len(tokens) == 2 and tokens[1] == '%' and tokens[0] <= 100:
                total_space = get_total_disk_space(opts.destination)
                opts.limit_disk_usage = int(total_space / 100 * int(tokens[0]))
                log.info('Settings disk usage limit to %s', hf.format_size(opts.limit_disk_usage, binary=True))
            else:
                print('Unexpected disk usage limit')
                exit(1)
        else:
            opts.limit_disk_usage = hf.parse_size(opts.limit_disk_usage, binary=True)


def get_total_disk_space(path):
    fs_stat = os.statvfs(path)
    return fs_stat.f_blocks * fs_stat.f_frsize


def get_available_disk_space(path):
    fs_stat = os.statvfs(path)
    return fs_stat.f_bfree * fs_stat.f_frsize


def get_plex_client(opts):
    import keyring
    import plexapi

    plexapi.X_PLEX_IDENTIFIER = db.get_client_uuid()
    plexapi.BASE_HEADERS['X-Plex-Client-Identifier'] = plexapi.X_PLEX_IDENTIFIER

    plexapi.X_PLEX_PRODUCT = 'plexiglas'
    plexapi.BASE_HEADERS['X-Plex-Product'] = plexapi.X_PLEX_PRODUCT

    plexapi.X_PLEX_PROVIDES = 'sync-target'
    plexapi.BASE_HEADERS['X-Plex-Sync-Version'] = '2'
    plexapi.BASE_HEADERS['X-Plex-Provides'] = plexapi.X_PLEX_PROVIDES

    # mimic iPhone SE
    plexapi.X_PLEX_PLATFORM = 'iOS'
    plexapi.X_PLEX_PLATFORM_VERSION = '11.4.1'
    plexapi.X_PLEX_DEVICE = 'iPhone'

    plexapi.BASE_HEADERS['X-Plex-Platform'] = plexapi.X_PLEX_PLATFORM
    plexapi.BASE_HEADERS['X-Plex-Platform-Version'] = plexapi.X_PLEX_PLATFORM_VERSION
    plexapi.BASE_HEADERS['X-Plex-Device'] = plexapi.X_PLEX_DEVICE
    plexapi.BASE_HEADERS['X-Plex-Model'] = '8,4'
    plexapi.BASE_HEADERS['X-Plex-Vendor'] = 'Apple'

    plexapi.X_PLEX_ENABLE_FAST_CONNECT = True

    plexapi.TIMEOUT = 120

    plex = None

    log.info('Logging to myplex with username %s', opts.username)

    token = keyring.get_password('plexiglas', 'token_' + opts.username)
    if opts.username and opts.password:
        log.debug('Password-based')
        from plexapi.myplex import MyPlexAccount
        plex = MyPlexAccount(opts.username, opts.password)
        keyring.set_password('plexiglas', 'token_' + opts.username, plex.authenticationToken)
    elif opts.username and token:
        log.debug('Token-based')
        from plexapi.myplex import MyPlexAccount
        plex = MyPlexAccount(opts.username, token=token)

    return plex


def init_logging(opts):
    log.propagate = False
    if opts.log_file:
        from logging.handlers import RotatingFileHandler
        lh = RotatingFileHandler(opts.log_file, maxBytes=int(opts.log_file_max_size), backupCount=opts.log_file_backups)
    else:
        lh = logging.StreamHandler(sys.stdout)

    log.addHandler(lh)

    if opts.debug or opts.verbose:
        log_format = '[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s:%(lineno)d] %(message)s'
    else:
        log_format = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'

    lh.setFormatter(logging.Formatter(log_format,
                                      datefmt='%d/%m/%Y %H:%M:%S'))

    if opts.debug:
        log.setLevel(logging.DEBUG)
        logging.basicConfig(format=log_format, datefmt='%d/%m/%Y %H:%M:%S')
    else:
        log.setLevel(logging.INFO)

    if not opts.verbose:
        from plexapi import log as plexapi_log
        plexapi_log.disabled = True


def pretty_filename(media, part):
    """

    :param media:
    :type media: plexapi.base.Playable
    :param part:
    :type part: plexapi.media.MediaPart
    :return str
    """

    from plexapi import video

    ret = media._prettyfilename()
    if isinstance(media, video.Movie):
        if media.year:
            ret += ' (%s)' % media.year

    return '%s.%s' % (ret, part.container)


def main():
    from plexapi import utils

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-u', '--username', help='Your Plex username')
    parser.add_argument('-p', '--password', help='Your Plex password')
    parser.add_argument('-d', '--destination', help='Download destination', default=os.getcwd())
    parser.add_argument('-w', '--mark-watched', help='Mark missing media as watched', action='store_const', const=True,
                        default=False)
    parser.add_argument('--debug', help='Enable debug logging', action='store_const', const=True, default=False)
    parser.add_argument('-v', '--verbose', help='Enable logging from plexapi', action='store_const', const=True,
                        default=False)
    parser.add_argument('-s', '--limit-disk-usage', help='Limit total downloaded files size (eg 1G, 100M, 10%)')

    parser.add_argument('-l', '--log-file', help='Save logs to the specified file', default=None)
    parser.add_argument('--log-file-max-size', help='Maximum log file size in bytes', default='1M')
    parser.add_argument('--log-file-backups', help='Count of log files to store', default=3)
    parser.add_argument('--loop', help='Run the script for indefinite amount of time', default=False,
                        action='store_const', const=True)
    parser.add_argument('--delay', help='Delay between iterations (only with --loop)', default=60)

    opts = parser.parse_args()

    process_opts(opts)

    plex = get_plex_client(opts)

    last_reported_du = 0

    stop = False
    while not stop:
        stop = not opts.loop

        if not os.path.isdir(opts.destination):
            if stop:
                log.error('Destination directory does not exists')
                exit(1)
            log.debug('Destination directory is not found, probably external storage was disconnected, going to sleep')
            sleep(int(opts.delay))
            continue

        disk_used = db.get_downloaded_size()
        disk_used_hf = hf.format_size(disk_used, binary=True)
        if disk_used > 0 and disk_used_hf != last_reported_du:
            last_reported_du = disk_used_hf
            log.info('Currently used (according to DB): %s', disk_used_hf)

        try:
            sync_items = plex.syncItems().items
            required_media = []
            sync_list_without_changes = []
            disk_used = db.get_downloaded_size()

            all_downloaded_items = db.get_all_downloaded()
            downloaded_count = defaultdict(lambda: defaultdict(int))

            for (machine_id, sync_id), items in groupby(all_downloaded_items, key=itemgetter(1, 2)):
                downloaded_count[machine_id][sync_id] = len(list(items))

            for item in sync_items:
                log.debug('Checking sync item#%d %s', item.id, item.title)

                if item.status.itemsReadyCount == 0\
                        and item.status.itemsDownloadedCount == downloaded_count[item.machineIdentifier][item.id]:
                    sync_list_without_changes.append((item.machineIdentifier, item.id))
                    log.debug('No changes for the item %s', item.status)
                    continue

                for media in item.getMedia():
                    log.debug('Checking media#%d %s', media.ratingKey, media.title)
                    required_media.append((item.machineIdentifier, item.id, media.ratingKey))
                    for part in media.iterParts():
                        if part.syncItemId == item.id and part.syncState == 'processed':
                            filename = pretty_filename(media, part)

                            if opts.limit_disk_usage and disk_used + part.size > opts.limit_disk_usage:
                                log.debug('Not downloading %s from %s, size limit would be exceeded', filename, item.title)
                                continue

                            if get_available_disk_space(opts.destination) < part.size:
                                log.debug('Not downloading %s from %s, due to low available space', filename, item.title)
                                continue

                            savepath = os.path.join(opts.destination, item.title)
                            url = part._server.url(part.key)
                            log.info('Downloading %s to %s', filename, savepath)
                            os.makedirs(savepath, exist_ok=True)

                            path = os.path.join(savepath, filename)
                            try:
                                if not os.path.isfile(path) or os.path.getsize(path) != part.size:
                                    utils.download(url, token=plex.authenticationToken, filename=filename,
                                                   savepath=savepath, session=media._server._session, showstatus=True)
                                db.mark_downloaded(item, media, part.size, filename)
                                item.markDownloaded(media)
                                disk_used += part.size
                            except:
                                if os.path.isfile(path) and os.path.getsize(path) != part.size:
                                    os.unlink(path)
                                raise

                            break

            for (db_item_id, machine_id, sync_id, media_id, sync_title, media_filename) in db.get_all_downloaded():
                media_path = os.path.join(opts.destination, sync_title, media_filename)
                if (machine_id, sync_id, media_id) in required_media or (machine_id, sync_id) in sync_list_without_changes:
                    if not os.path.isfile(media_path):
                        if opts.mark_watched:
                            conn = None
                            for res in plex.resources():
                                if res.clientIdentifier == machine_id:
                                    conn = res.connect()
                                    break

                            if conn:
                                key = '/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % media_id
                                conn.query(key)
                                log.info('File %s not found, marking media as watched', media_path)
                                db.remove_downloaded(db_item_id)
                        else:
                            log.error('File not found %s, removing it from the DB', media_path)
                            db.remove_downloaded(db_item_id)
                else:
                    log.info('File is not required anymore %s', media_path)
                    if os.path.isfile(media_path):
                        os.unlink(media_path)
                    db.remove_downloaded(db_item_id)
        except ReadTimeout:
            if stop:
                raise
            else:
                log.info('Oops, I`ve got a ReadTimeout, let`s try again')
                plex = get_plex_client(opts)

        if not stop:
            log.debug('Going to sleep')
            sleep(int(opts.delay))


if __name__ == '__main__':
    main()
