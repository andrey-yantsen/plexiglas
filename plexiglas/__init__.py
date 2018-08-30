"""
Plexiglas is a script which helps you to copy your content from a Plex server to any other storage.
I'm using it especially for copying movies and tv-shows from my main server to a "travel" instance, which is set up
on my external HDD (WD My Passport Wireless Pro).
"""

__version__ = '0.1.5'

import logging

try:
    import keyring
    from keyring.core import set_keyring
except ImportError:
    import keyring_stub as keyring
    set_keyring = lambda x: None


log = logging.getLogger('plexiglas')
