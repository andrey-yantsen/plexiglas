from humanfriendly import format_size
from plexapi.exceptions import BadRequest
import platform

from . import db, log
import os
from .token_bucket import rate_limit as limit_bandwidth


def cleanup(plex, sync_type, required_media, opts):
    for row in db.get_all_downloaded(sync_type):
        sync_title = row['sync_title']
        if '#' in sync_title:
            sync_title, _ = sync_title.split('#', 1)
            sync_title = sync_title.strip()

        sync_title = sanitize_filename(sync_title, True)
        media_filename = sanitize_filename(row['media_filename'])

        if row['media_type'] == 'movie' and opts.subdir:
            media_path = os.path.join(opts.destination, sync_title, os.path.splitext(media_filename)[0], media_filename)
        else:
            media_path = os.path.join(opts.destination, sync_title, media_filename)
        if (row['machine_id'], row['media_id']) in required_media:
            if not os.path.isfile(media_path):
                if opts.mark_watched:
                    conn = None
                    for res in plex.resources():
                        if res.clientIdentifier == row['machine_id']:
                            conn = res.connect()
                            break

                    if conn:
                        log.info('File %s not found, marking media as watched', media_path)
                        try:
                            item = conn.fetchItem(int(row['media_id']))
                            if hasattr(item, 'markWatched'):
                                item.markWatched()
                        except BadRequest as e:
                            if 'not_found' not in str(e):
                                raise
                        db.remove_downloaded(row['machine_id'], sync_type, row['sync_id'], row['media_id'])
                    else:
                        log.error('Unable to find server %s', row['machine_id'])
                else:
                    log.error('File not found %s, removing it from the DB', media_path)
                    db.remove_downloaded(row['machine_id'], sync_type, row['sync_id'], row['media_id'])
        else:
            log.info('File is not required anymore %s', media_path)
            if os.path.isfile(media_path):
                os.unlink(media_path)
            db.remove_downloaded(row['machine_id'], sync_type, row['sync_id'], row['media_id'])


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
    if platform.system() == 'Windows':
        import ctypes
        total_bytes = ctypes.c_ulonglong(0)
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, ctypes.pointer(total_bytes), None)
        if ok:
            total_space = total_bytes.value
        else:
            total_space = 0
    else:
        fs_stat = os.statvfs(path)
        total_space = fs_stat.f_blocks * fs_stat.f_frsize

    return total_space


def get_available_disk_space(path):
    if platform.system() == 'Windows':
        import ctypes
        free_bytes = ctypes.c_ulonglong(0)
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
        if ok:
            free_space = free_bytes.value
        else:
            free_space = 0
    else:
        fs_stat = os.statvfs(path)
        free_space = fs_stat.f_bfree * fs_stat.f_frsize
    return free_space


def makedirs(name, mode=0o777, exist_ok=False):
    """ Mimicks os.makedirs() from Python 3. """
    try:
        os.makedirs(name, mode)
    except OSError:
        if not os.path.isdir(name) or not exist_ok:
            raise


def download(url, token, session, filename, savepath=None, chunksize=4024,
             showstatus=False, rate_limit=None):
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

    from requests import codes
    from plexapi import TIMEOUT

    # make sure the savepath directory exists
    savepath = savepath or os.getcwd()
    makedirs(savepath, exist_ok=True)
    filename = os.path.basename(filename)
    fullpath = os.path.join(savepath, filename)

    # fetch the data to be saved
    headers = {'X-Plex-Token': token}

    if os.path.isfile(fullpath):
        headers['Range'] = 'bytes=%d-' % os.path.getsize(fullpath)

    response = session.get(url, headers=headers, stream=True, timeout=TIMEOUT)

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
    bar = None
    if showstatus:
        from .tqdm_stub import tqdm

        total = int(response.headers.get('content-length', 0))
        initial = 0

        if headers.get('Range') and response.status_code == codes.partial_content:
            initial = os.path.getsize(fullpath)
            total += initial

        bar = tqdm(unit='B', unit_scale=True, total=total, desc=filename, initial=initial)

    if rate_limit and 0 < rate_limit < chunksize:
        chunksize = rate_limit

    with open(fullpath, file_mode) as handle:
        iter_content = response.iter_content(chunk_size=chunksize)

        if rate_limit and rate_limit > 0:
            iter_content = limit_bandwidth(iter_content, rate_limit)

        for chunk in iter_content:
            handle.write(chunk)
            if bar is not None:
                bar.update(len(chunk))

    if bar:
        bar.close()

    return fullpath


def sanitize_filename(filename, allow_dir_separator=False):
    if allow_dir_separator:
        filename = os.path.normpath(filename)
    else:
        filename = filename.replace('/', '_').replace('\\', '_')

    for c in ['?', ';', ':', '+', '<', '>', '|', '*', '"']:
        filename = filename.replace(c, '_')
    for c in range(0, 31):
        filename = filename.replace(chr(c), '_')
    old_file_name = filename
    filename.replace('__', '_')
    while old_file_name != filename:
        old_file_name = filename
        filename.replace('__', '_')
    return filename


def download_media(plex, sync_title, media, part, opts, downloaded_callback, max_allowed_size_diff_percent=0):
    log.debug('Checking media#%d %s', media.ratingKey, media.title)
    filename = sanitize_filename(pretty_filename(media, part))
    filename_tmp = filename + '.part'

    if '#' in sync_title:
        sync_title, _ = sync_title.split('#', 1)
        sync_title = sync_title.strip()

    savepath = os.path.join(opts.destination, sanitize_filename(sync_title, True))

    if os.sep.join(os.path.join(savepath, filename).split(os.sep)[-2:]) in opts.skip:
        log.info('Skipping file %s from %s due to cli arguments', filename, savepath)
        return

    if media.TYPE == 'movie' and opts.subdir:
        savepath = os.path.join(savepath, sanitize_filename(os.path.splitext(filename)[0]))

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

    if not os.path.isfile(path_tmp) or abs(1 - os.path.getsize(path_tmp) / part.size) > max_allowed_size_diff_percent:
        log.error('File "%s" has an unexpected size (actual: %d, expected: %d)', path_tmp,
                  os.path.getsize(path_tmp), part.size)
        raise ValueError('Downloaded file size is not the same as expected')

    downloaded_callback(media, part, filename)

    os.rename(path_tmp, path)
