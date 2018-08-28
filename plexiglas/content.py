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


def makedirs(name, mode=0o777, exist_ok=False):
    """ Mimicks os.makedirs() from Python 3. """
    try:
        os.makedirs(name, mode)
    except OSError:
        if not os.path.isdir(name) or not exist_ok:
            raise


def download(url, token, session, filename, savepath=None, chunksize=4024,
             showstatus=False):
    """ Helper to download a thumb, videofile or other media item. Returns the local
        path to the downloaded file.

        Copied from plexapi.utils.download

        Parameters:
            url (str): URL where the content be reached.
            token (str): Plex auth token to include in headers.
            savepath (str): Defaults to current working dir.
            chunksize (int): What chunksize read/write at the time.
            showstatus(bool): Display a progressbar.

        Example:
            >>> download(a_episode.getStreamURL(), a_episode.location)
            /path/to/file
    """

    from . import log
    from requests import codes

    # make sure the savepath directory exists
    savepath = savepath or os.getcwd()
    makedirs(savepath, exist_ok=True)
    filename = os.path.basename(filename)
    fullpath = os.path.join(savepath, filename)

    # fetch the data to be saved
    headers = {'X-Plex-Token': token}

    if os.path.isfile(fullpath):
        headers['Range'] = 'bytes=%d-' % os.path.getsize(fullpath)

    response = session.get(url, headers=headers, stream=True)

    # append file.ext from content-type if not already there
    extension = os.path.splitext(fullpath)[-1]
    if not extension:
        contenttype = response.headers.get('content-type')
        if contenttype and 'image' in contenttype:
            fullpath += contenttype.split('/')[1]

    if headers.get('Range') and response.status_code == codes.partial_content:
        file_mode = 'ab'
    else:
        file_mode = 'wb'

    # save the file to disk
    if showstatus:  # pragma: no cover
        from tqdm import tqdm
        total = int(response.headers.get('content-length', 0))
        initial = 0

        if headers.get('Range') and response.status_code == codes.partial_content:
            initial = os.path.getsize(fullpath)
            total += initial

        bar = tqdm(unit='B', unit_scale=True, total=total, desc=filename, initial=initial)

    with open(fullpath, file_mode) as handle:
        for chunk in response.iter_content(chunk_size=chunksize):
            handle.write(chunk)
            if showstatus:
                bar.update(len(chunk))

    if showstatus:  # pragma: no cover
        bar.close()

    return fullpath
