from collections import defaultdict
from itertools import groupby
from operator import itemgetter
from keyring.util import properties

from . import log, db
from .content import get_available_disk_space, download_media
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

                    def mark_downloaded(media, part, filename):
                        db.mark_downloaded(item.machineIdentifier, cls.name, item.id, item.title, media, part.size,
                                           filename, sync_version=item.version)
                        item.markDownloaded(media)

                    download_media(plex, item.title, media, part, opts, mark_downloaded)

        if len(skipped_syncs):
            for machine_id, sync_infos in groupby(skipped_syncs, key=lambda item: item[0]):
                downloaded_media = db.get_downloaded_for_sync(machine_id, cls.name, [s[1] for s in sync_infos])

                for m in downloaded_media:
                    required_media.append((machine_id, m['media_id']))

        return required_media
