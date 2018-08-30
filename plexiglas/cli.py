import os
import argparse
import logging
import sys
from time import sleep
import humanfriendly as hf

from . import log, keyring, set_keyring


def process_opts(opts):
    from .content import makedirs

    init_logging(opts)

    if opts.insecure:
        from keyrings.cryptfile.file import PlaintextKeyring
        set_keyring(PlaintextKeyring())

    if opts.username:
        log.debug('Username provided, updating in keyring')
        keyring.set_password('plexiglas', 'myplex_login', opts.username)
    else:
        log.debug('No username in args')
        opts.username = keyring.get_password('plexiglas', 'myplex_login')

        if not opts.username:
            from six.moves import input
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

    opts.destination = os.path.realpath(os.path.expanduser(opts.destination))

    if not os.access(opts.destination, os.W_OK):
        try:
            makedirs(opts.destination, exist_ok=True)
        except OSError:
            print('Directory "%s" should be writable' % opts.destination)
            exit(1)

    os.chdir(opts.destination)

    if opts.limit_disk_usage:
        if '%' in opts.limit_disk_usage:
            tokens = hf.tokenize(opts.limit_disk_usage)
            if len(tokens) == 2 and tokens[1] == '%' and tokens[0] <= 100:
                from .content import get_total_disk_space

                total_space = get_total_disk_space(opts.destination)
                opts.limit_disk_usage = int(total_space / 100 * int(tokens[0]))
                log.info('Setting disk usage limit to %s', hf.format_size(opts.limit_disk_usage, binary=True))
            else:
                print('Unexpected disk usage limit')
                exit(1)
        else:
            opts.limit_disk_usage = hf.parse_size(opts.limit_disk_usage, binary=True)

    if opts.rate_limit and not opts.rate_limit.isdigit():
        opts.rate_limit = hf.parse_size(opts.rate_limit, binary=True)


def init_logging(opts):
    log.propagate = False

    if opts.log_file_max_size:
        opts.log_file_max_size = hf.parse_size(opts.log_file_max_size, binary=True)

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


def parse_arguments():
    from platform import uname

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-u', '--username', help='Your Plex username')
    parser.add_argument('-p', '--password', help='Your Plex password')
    parser.add_argument('-d', '--destination', help='Download destination (default "%(default)s")', default=os.getcwd())
    parser.add_argument('-w', '--mark-watched', help='Mark missing media as watched', action='store_const', const=True,
                        default=False)
    parser.add_argument('--debug', help='Enable debug logging', action='store_const', const=True, default=False)
    parser.add_argument('-v', '--verbose', help='Enable logging from plexapi', action='store_const', const=True,
                        default=False)
    parser.add_argument('-s', '--limit-disk-usage', help='Limit total downloaded files size (eg 1G, 100M, 10%%)')

    parser.add_argument('-l', '--log-file', help='Save logs to the specified file', default=None)
    parser.add_argument('--log-file-max-size', help='Maximum log file size in bytes (default %(default)s)',
                        default='1M')
    parser.add_argument('--log-file-backups', help='Count of log files` backups to store (default %(default)d)',
                        default=3)
    parser.add_argument('--loop', help='Run the script for indefinite amount of time', default=False,
                        action='store_const', const=True)
    parser.add_argument('--delay', help='Delay in seconds between iterations (only with --loop, default %(default)d)',
                        default=60)
    parser.add_argument('-n', '--device-name', help='Device name for the Plex client instance to be displayed in '
                                                    'devices list (default "%(default)s")', default=uname()[1])
    parser.add_argument('-r', '--resume-downloads', help='Allow to resume downloads (the result file may be broken)',
                        action='store_const', const=True, default=False)
    parser.add_argument('--rate-limit', help='Limit bandwidth usage per second (e.g. 1M, 100K)')
    parser.add_argument('-q', help='Terminate right after saving all required data to keyring', default=False,
                        action='store_const', const=True)
    parser.add_argument('-i', '--insecure', help='Store your password with minimal encryption, without requiring'
                                                 'additional password (useful when running headless on some strange '
                                                 'devices like WD My Passport Wireless Pro)',
                        default=False, action='store_const', const=True)

    return parser.parse_args()


def main():
    from .plex import get_plex_client
    from .content import cleanup
    from . import plexsync
    from . import db
    from requests import exceptions

    opts = parse_arguments()
    process_opts(opts)

    if opts.q:
        get_plex_client(opts)
        exit(0)

    last_reported_du = None

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
            plex = get_plex_client(opts)
            required_media, sync_list_without_changes = plexsync.sync(plex, opts.destination, opts.limit_disk_usage,
                                                                      opts.resume_downloads, opts.rate_limit)
            cleanup(opts.destination, opts.mark_watched, required_media, sync_list_without_changes, plex)
        except exceptions.RequestException:
            if stop:
                raise
            else:
                log.exception('Got exception from RequestException family, it shouldn`t be anything serious')

        if not stop:
            log.debug('Going to sleep for %d seconds', opts.delay)
            sleep(int(opts.delay))


if __name__ == '__main__':
    main()
