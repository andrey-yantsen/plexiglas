from collections import defaultdict
from itertools import groupby
from operator import itemgetter
import os
from humanfriendly import format_size
from keyring.util import properties

from . import log, db
from .content import pretty_filename, get_available_disk_space
from .plugin import PlexiglasPlugin


class MobileSync(PlexiglasPlugin):
    @properties.ClassProperty
    @classmethod
    def priority(cls):
        return 100

    @classmethod
    def get_download_part(cls, media, sync_item):
        for part in media.iterParts():
            if part.syncItemId == sync_item.id and part.syncState == 'processed':
                return part

    @classmethod
    def download_media(cls, plex, sync_item, media, part, opts):
        from .content import makedirs, download

        log.debug('Checking media#%d %s', media.ratingKey, media.title)
        filename = pretty_filename(media, part)
        filename_tmp = filename + '.part'

        savepath = os.path.join(opts.destination, sync_item.title)

        if os.sep.join(os.path.join(savepath, filename).split(os.sep)[-2:]) in opts.skip:
            log.info('Skipping file %s from %s due to cli arguments', filename, savepath)
            return

        if media.TYPE == 'movie' and opts.subdir:
            savepath = os.path.join(savepath, os.path.splitext(filename)[0])

        part_key = part.key
        if part.decision == 'directplay':
            part_key = '/' + '/'.join(part_key.split('/')[3:])
        url = part._server.url(part_key)
        log.info('Downloading %s to %s, file size is %s', filename, savepath, format_size(part.size, binary=True))
        makedirs(savepath, exist_ok=True)

        path = os.path.join(savepath, filename)
        path_tmp = os.path.join(savepath, filename_tmp)

        if not opts.resume_downloads and os.path.isfile(path_tmp) and os.path.getsize(path_tmp) != part.size:
            os.unlink(path_tmp)

        if os.path.isfile(path_tmp) and os.path.getsize(path_tmp) > part.size:
            log.error('File "%s" has an unexpected size (actual: %d, expected: %d), removing it', path_tmp,
                      os.path.getsize(path_tmp), part.size)
            os.unlink(path_tmp)

        if not os.path.isfile(path_tmp) or os.path.getsize(path_tmp) != part.size:
            try:
                download(url, token=plex.authenticationToken, session=media._server._session, filename=filename_tmp,
                         savepath=savepath, showstatus=True, rate_limit=opts.rate_limit)
            except BaseException:  # handle all exceptions, anyway we'll re-raise them
                if os.path.isfile(path_tmp) and os.path.getsize(path_tmp) != part.size and not opts.resume_downloads:
                    os.unlink(path_tmp)
                raise

        if not os.path.isfile(path_tmp) or os.path.getsize(path_tmp) != part.size:
            log.error('File "%s" has an unexpected size (actual: %d, expected: %d)', path_tmp,
                      os.path.getsize(path_tmp), part.size)
            raise ValueError('Downloaded file size is not the same as expected')

        db.mark_downloaded(sync_item, media, part.size, filename)
        sync_item.markDownloaded(media)

        os.rename(path_tmp, path)

    @classmethod
    def sync(cls, plex, opts):
        sync_items = plex.syncItems().items
        required_media = []
        disk_used = db.get_downloaded_size()

        all_downloaded_items = db.get_all_downloaded(cls.name)
        downloaded_count = defaultdict(lambda: defaultdict(int))

        for (machine_id, sync_id), items in groupby(all_downloaded_items, key=itemgetter(1, 2)):
            downloaded_count[machine_id][sync_id] = len(list(items))

        skipped_syncs = []

        for item in sync_items:
            log.debug('Checking sync item#%d %s', item.id, item.title)

            if item.status.itemsReadyCount == 0 \
                    and item.status.itemsDownloadedCount == downloaded_count[item.machineIdentifier][item.id]:
                skipped_syncs.append((item.machineIdentifier, item.id))
                log.debug('No changes for the item#%d %s', item.id, item.status)
                continue

            if opts.limit_disk_usage and disk_used > opts.limit_disk_usage:
                skipped_syncs.append((item.machineIdentifier, item.id))
                log.debug('Disk limit exceeded, skipping item#%d', item.id)
                continue

            for media in item.getMedia():
                required_media.append((item.machineIdentifier, media.ratingKey))
                part = cls.get_download_part(media, item)
                if part:
                    if opts.limit_disk_usage and disk_used + part.size > opts.limit_disk_usage:
                        log.debug('Not downloading %s from %s, size limit would be exceeded', media.title,
                                  item.title)
                        continue

                    if get_available_disk_space(opts.destination) < part.size:
                        log.debug('Not downloading %s from %s, due to low available space', media.title, item.title)
                        continue

                    cls.download_media(plex, item, media, part, opts)

        if len(skipped_syncs):
            for machine_id, sync_infos in groupby(skipped_syncs, key=lambda item: item[0]):
                downloaded_media = db.get_downloaded_for_sync(machine_id, cls.name, [s[1] for s in sync_infos])

                for m in downloaded_media:
                    required_media.append((machine_id, m['media_id']))

        return required_media
