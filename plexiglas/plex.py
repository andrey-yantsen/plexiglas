from . import db, log


PLEXAPI_INITIALIZED = False


def init_sync_target():
    import plexapi

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


def init_plexapi(device_name):
    global PLEXAPI_INITIALIZED

    if PLEXAPI_INITIALIZED is True:
        return

    import plexapi

    plexapi.X_PLEX_IDENTIFIER = db.get_client_uuid()
    plexapi.BASE_HEADERS['X-Plex-Client-Identifier'] = plexapi.X_PLEX_IDENTIFIER

    plexapi.X_PLEX_DEVICE_NAME = device_name
    plexapi.BASE_HEADERS['X-Plex-Device-Name'] = plexapi.X_PLEX_DEVICE_NAME

    plexapi.X_PLEX_PRODUCT = 'plexiglas'
    plexapi.BASE_HEADERS['X-Plex-Product'] = plexapi.X_PLEX_PRODUCT

    init_sync_target()

    plexapi.X_PLEX_ENABLE_FAST_CONNECT = True

    plexapi.TIMEOUT = 120
    PLEXAPI_INITIALIZED = True


def get_plex_client(opts):
    from . import keyring

    init_plexapi(opts.device_name)

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
