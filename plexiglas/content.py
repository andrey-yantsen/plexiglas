from . import db, log
import os


def cleanup(path, mark_watched, required_media, sync_list_without_changes, plex):
    for (db_item_id, machine_id, sync_id, media_id, sync_title, media_filename) in db.get_all_downloaded():
        media_path = os.path.join(path, sync_title, media_filename)
        if (machine_id, media_id) in required_media or (machine_id, sync_id) in sync_list_without_changes:
            if not os.path.isfile(media_path):
                if mark_watched:
                    conn = None
                    for res in plex.resources():
                        if res.clientIdentifier == machine_id:
                            conn = res.connect()
                            break

                    if conn:
                        key = '/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % media_id
                        conn.query(key)
                        log.info('File %s not found, marking media as watched', media_path)
                        db.remove_downloaded(machine_id, sync_id, media_id)
                    else:
                        log.error('Unable to find server %s', machine_id)
                else:
                    log.error('File not found %s, removing it from the DB', media_path)
                    db.remove_downloaded(machine_id, sync_id, media_id)
        else:
            log.info('File is not required anymore %s', media_path)
            if os.path.isfile(media_path):
                os.unlink(media_path)
            db.remove_downloaded(machine_id, sync_id, media_id)


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
    if isinstance(media, video.Movie) and media.year:
        ret += ' (%s)' % media.year

    return '%s.%s' % (ret, part.container)


def get_total_disk_space(path):
    fs_stat = os.statvfs(path)
    return fs_stat.f_blocks * fs_stat.f_frsize


def get_available_disk_space(path):
    fs_stat = os.statvfs(path)
    return fs_stat.f_bfree * fs_stat.f_frsize
