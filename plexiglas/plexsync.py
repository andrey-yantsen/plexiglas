from collections import defaultdict
from itertools import groupby
from operator import itemgetter

from . import log
from .content import pretty_filename, get_available_disk_space
from . import db
import os


def get_download_part(media, sync_item):
    for part in media.iterParts():
        if part.syncItemId == sync_item.id and part.syncState == 'processed':
            return part


def download_media(part, media, sync_item, path, plex):
    from plexapi import utils

    log.debug('Checking media#%d %s', media.ratingKey, media.title)
    filename = pretty_filename(media, part)

    savepath = os.path.join(path, sync_item.title)
    url = part._server.url(part.key)
    log.info('Downloading %s to %s', filename, savepath)
    os.makedirs(savepath, exist_ok=True)

    path = os.path.join(savepath, filename)
    try:
        if not os.path.isfile(path) or os.path.getsize(path) != part.size:
            utils.download(url, token=plex.authenticationToken, filename=filename,
                           savepath=savepath, session=media._server._session, showstatus=True)
        db.mark_downloaded(sync_item, media, part.size, filename)
        sync_item.markDownloaded(media)
    except:
        if os.path.isfile(path) and os.path.getsize(path) != part.size:
            os.unlink(path)
        raise


def sync(plex, destination, limit_disk_usage):
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

        if item.status.itemsReadyCount == 0 \
                and item.status.itemsDownloadedCount == downloaded_count[item.machineIdentifier][item.id]:
            sync_list_without_changes.append((item.machineIdentifier, item.id))
            log.debug('No changes for the item#d %s', item.id, item.status)
            continue

        if limit_disk_usage and disk_used > limit_disk_usage:
            sync_list_without_changes.append((item.machineIdentifier, item.id))
            log.debug('Disk limit exceeded, skipping item#%d', item.id)
            continue

        for media in item.getMedia():
            required_media.append((item.machineIdentifier, media.ratingKey))
            part = get_download_part(media, item)
            if part:
                if limit_disk_usage and disk_used + part.size > limit_disk_usage:
                    log.debug('Not downloading %s from %s, size limit would be exceeded', media.title,
                              item.title)
                    continue

                if get_available_disk_space(destination) < part.size:
                    log.debug('Not downloading %s from %s, due to low available space', media.title, item.title)
                    continue

                download_media(part, media, item, destination, plex)

    return required_media, sync_list_without_changes
