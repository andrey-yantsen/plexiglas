from keyring.util.properties import ClassProperty

from plexiglas.content import download_media
from plexiglas.plugin import PlexiglasPlugin
import argparse
from plexiglas import log, db
from six.moves.urllib.parse import urlparse, parse_qsl, urlencode
from hashlib import md5
from plexapi import video, audio


class SimpleSync(PlexiglasPlugin):
    @ClassProperty
    @classmethod
    def priority(cls):
        return 10

    @classmethod
    def get_download_part(cls, media):
        for part in media.iterParts():
            return part

    @classmethod
    def sync(cls, plex, opts):
        required_media = []

        for target in opts.simple_sync_url:
            url = target[0]
            limit = target[1] if len(target) > 1 else -1
            unwatched_only = bool(target[2] if len(target) > 2 else 1)
            log.debug('Processing %s, with limit=%d, unwatched_only=%d', url, limit, unwatched_only)

            parsed_url = urlparse(url)

            if parsed_url.fragment[0] == '!' and '/server/' in parsed_url.fragment and 'key=' in parsed_url.fragment:
                parsed_url = urlparse(parsed_url.fragment)

            qs = dict(parse_qsl(parsed_url.query))
            splitted_url = parsed_url.path.split('/')

            machine_id = None
            for idx, value in enumerate(splitted_url):
                if value == 'server' and len(splitted_url) > idx + 1:
                    machine_id = splitted_url[idx + 1]
                    break

            if machine_id is None:
                raise ValueError('Unable to determinate server id for URL %s', url)

            server = None
            for resource in plex.resources():
                if resource.clientIdentifier == machine_id:
                    server = resource.connect()

            if server is None:
                raise ValueError('Unable to find required server in your MyPlex account')

            key = qs.pop('typeKey', qs.pop('key'))
            qs.pop('save', None)

            if qs.get('filters'):
                if '?' in key:
                    key += '&'
                else:
                    key += '?'

                key += qs.pop('filters')

            if len(qs):
                if '?' in key:
                    key += '&'
                else:
                    key += '?'
                key += urlencode(qs)

            sync_id = md5(key.encode('utf-8')).hexdigest()

            all_downloaded_media = [r['media_id'] for r in db.get_downloaded_for_sync_type(machine_id, cls.name)]
            items_list = server.fetchItems(key)

            section = None

            def mark_downloaded(media, part, filename):
                db.mark_downloaded(machine_id, cls.name, sync_id, section.title, media, part.size, filename)

            if len(items_list) == 1 and type(items_list[0]) in (video.Show, video.Season):
                root = items_list[0]
                if unwatched_only:
                    items_list = root.unwatched()
                else:
                    items_list = root.episodes()

                if isinstance(root, video.Show):
                    section = root
                elif isinstance(root, video.Season):
                    section = root.show()
            elif len(items_list) == 1 and type(items_list[0]) in (audio.Artist, audio.Album):
                root = items_list[0]
                items_list = root.tracks()

                if isinstance(root, audio.Artist):
                    section = root
                elif isinstance(root, audio.Album):
                    section = root.show()

            downloaded_count = 0
            for item in items_list:
                if -1 < limit == downloaded_count:
                    log.debug('Reached download limit, aborting')
                    break

                if isinstance(item, video.Video) and item.isWatched and unwatched_only:
                    continue

                required_media.append((machine_id, item.ratingKey))

                downloaded_count += 1

                if item.ratingKey in all_downloaded_media:
                    continue

                if section is None:
                    section = item.section()

                part = cls.get_download_part(item)
                max_allowed_size_diff_percent = 0
                if isinstance(item, audio.Track):
                    # Plex removes some tags from audio file, so the size may be a little lower, than expected
                    max_allowed_size_diff_percent = 1
                download_media(plex, section.title, item, part, opts, mark_downloaded, max_allowed_size_diff_percent)

        return required_media

    @classmethod
    def register_options(cls, parser):
        g = parser.add_argument_group(title='Simple sync')
        g.add_argument('--simple-sync-url', action=SimpleSyncArgparseUrlAction, nargs='+', metavar='URL [limit [all]]',
                       help='An url from Plex Web with optional limit, provided as integer >= -1, where -1 is '
                            'unlimited, and optional `all` flag, provided as 0 or 1, means to download all content, '
                            'not only unwatched', default=[])

    @classmethod
    def process_options(cls, opts):
        for target in opts.simple_sync_url:
            url = target[0]
            if '/server/' not in url:
                raise ValueError('Provided URL must contain /server/ part')

            if 'key=' not in url:
                raise ValueError('Provided URL must contain key= part')


class SimpleSyncArgparseUrlAction(argparse._AppendAction):
    def __call__(self, parser, args, values, option_string=None):
        if not 1 <= len(values) <= 3:
            msg = 'argument "{f}" requires between {nmin} and {nmax} arguments'.format(
                f=self.dest, nmin=1, nmax=3)
            raise argparse.ArgumentTypeError(msg)

        if len(values) > 1:
            if values[1].isdigit() and int(values[1]) >= -1:
                values[1] = int(values[1])
            else:
                msg = 'argument "{f}" requires requires `limit` to be specified as integer >=-1'.format(
                    f=self.dest)
                raise argparse.ArgumentTypeError(msg)

        if len(values) > 2:
            if values[2].isdigit() and int(values[2]) in (0, 1):
                values[2] = int(values[2])
            else:
                msg = 'argument "{f}" requires requires `all` to be specified as integer 0 or 1'.format(
                    f=self.dest)
                raise argparse.ArgumentTypeError(msg)

        super(SimpleSyncArgparseUrlAction, self).__call__(parser, args, values, option_string)
