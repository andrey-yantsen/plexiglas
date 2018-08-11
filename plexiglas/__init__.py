import os
import argparse

# Change default config path for PlexApi config reader
os.environ.setdefault('PLEXAPI_CONFIG_PATH', os.path.expanduser('~/.config/plexiglas/config.ini'))


def process_opts(opts):
    import keyring
    from plexapi import CONFIG

    if not CONFIG.has_section('auth'):
        CONFIG.add_section('auth')

    if not opts.username:
        opts.username = CONFIG.get('auth.myplex_username')

    if opts.username:
        if not CONFIG.get('auth.myplex_username'):
            CONFIG.set('auth', 'myplex_username', opts.username)
            with open(opts.config, 'wt') as f:
                CONFIG.write(f)

        if opts.password:
            keyring.set_password('plexiglas', opts.username, opts.password)
        else:
            if CONFIG.get('auth.myplex_password'):
                keyring.set_password('plexiglas', opts.username, CONFIG.get('auth.myplex_password'))

                with open(opts.config, 'wt') as f:
                    CONFIG.remove_option('auth', 'myplex_password')
                    CONFIG.write(f)

            opts.password = keyring.get_password('plexiglas', opts.username)

        if not opts.password:
            import getpass
            opts.password = getpass.getpass('Enter the plex.tv password for %s: ' % opts.username)
            keyring.set_password('plexiglas', opts.username, opts.password)


def init_plex_api():
    import plexapi
    from plexapi import sync

    plexapi.X_PLEX_PRODUCT = 'plexiglas'
    plexapi.BASE_HEADERS['X-Plex-Product'] = plexapi.X_PLEX_PRODUCT
    sync.init()


def get_plex_client(opts):
    import keyring

    init_plex_api()

    plex = None

    token = keyring.get_password('myplex', 'token_' + opts.username)
    if opts.username and opts.password:
        from plexapi.myplex import MyPlexAccount
        plex = MyPlexAccount(opts.username, opts.password)
        keyring.set_password('myplex', 'token_' + opts.username, plex.authenticationToken)
    elif opts.username and token:
        from plexapi.myplex import MyPlexAccount
        plex = MyPlexAccount(opts.username, opts.password)

    return plex


def analyze_myplex(plex):
    from plexapi import CONFIG

    for resource in plex.resources():
        if 'server' in resource.provides.split(','):
            print(f"Checking server '{resource.name}'...")

            config_section = 'server_' + resource.clientIdentifier

            if CONFIG.has_section(config_section):
                pass
            else:
                CONFIG.add_section(config_section)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-u', '--username', help='Your Plex username')
    parser.add_argument('-p', '--password', help='Your Plex password')
    parser.add_argument('-c', '--config', help='Config file path',
                        default=os.environ.get('PLEXAPI_CONFIG_PATH'))
    parser.add_argument('-d', '--destination', help='Download destination')

    opts = parser.parse_args()

    os.environ['PLEXAPI_CONFIG_PATH'] = opts.config

    process_opts(opts)
    plex = get_plex_client(opts)
    analyze_myplex(plex)

    item = plex.syncItems().items[0]
    for media in item.getMedia():
        for part in media.iterParts():
            pass


if __name__ == '__main__':
    main()
