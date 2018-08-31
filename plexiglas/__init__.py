"""
Plexiglas is a script which helps you to copy your content from a Plex server to any other storage.
I'm using it especially for copying movies and tv-shows from my main server to a "travel" instance, which is set up
on my external HDD (WD My Passport Wireless Pro).
"""

__version__ = '_CI_SET_VERSION_'

import logging

try:
    import keyring  # noqa: F401
    from keyring.core import set_keyring
except ImportError:
    import keyring_stub as keyring  # noqa: F401

    def set_keyring(x):
        pass


log = logging.getLogger('plexiglas')
