import abc

import entrypoints
from keyring.errors import ExceptionRaisedContext
from keyring.util import properties, once, suppress_exceptions
from six import add_metaclass

from . import log


class PlexiglasPluginMeta(abc.ABCMeta):
    """
    A metaclass that's both an ABCMeta and a type that keeps a registry of
    all (non-abstract) types.
    """

    def __init__(cls, name, bases, dict):
        super(PlexiglasPluginMeta, cls).__init__(name, bases, dict)
        if not hasattr(cls, '_classes'):
            cls._classes = set()
        classes = cls._classes
        if not cls.__abstractmethods__:
            classes.add(cls)


@add_metaclass(PlexiglasPluginMeta)
class PlexiglasPlugin:
    """
    You can implement following classmethods to work with the workflow:

    Bootstrap:
        def register_options(cls, parser)
        def process_options(cls, opts)

    Synchronization:
        def sync(cls, plex, opts): list
    """

    @abc.abstractproperty
    def priority(cls):
        """
        Each plugin class must supply a priority, a number (float or integer)
        indicating the priority of the backend relative to all other plugins.
        The priority need not be static -- it may (and should) vary based
        attributes of the environment in which is runs (platform, available
        packages, etc.).

        A higher number indicates a higher priority. The priority should raise
        a RuntimeError with a message indicating the underlying cause if the
        backend is not suitable for the current environment.

        As a rule of thumb, a priority between zero but less than one is
        suitable, but a priority of one or greater is recommended.
        """

    @properties.ClassProperty
    @classmethod
    def viable(cls):
        with ExceptionRaisedContext() as exc:
            cls.priority
        return not bool(exc)

    @properties.ClassProperty
    @classmethod
    def name(cls):
        return '%s.%s' % (cls.__module__, cls.__name__)


def _load_plugins():
    """
    Locate all setuptools entry points by the name 'plexiglas plugins' and initialize them.
    Any third-party library may register an entry point by adding the following to their setup.py::

        entry_points = {
            'plexiglas.plugins': [
                'plugin_name = mylib.mymodule:initialize_func',
            ],
        },

    `plugin_name` can be anything, and is only used to display the name
    of the plugin at initialization time.

    `initialize_func` is optional, but will be invoked if callable.
    """
    group = 'plexiglas.plugins'
    entry_points = entrypoints.get_group_all(group=group)
    for ep in entry_points:
        try:
            log.info('Loading plugin %s', ep.name)
            init_func = ep.load()
            if callable(init_func):
                init_func()
        except Exception:
            log.exception("Error initializing plugin %s." % ep)


@once
def get_all_plugins():
    """
    Return a list of all implemented plugins that can be constructed without
    parameters.
    """
    _load_plugins()

    def is_class_viable(keyring_cls):
        try:
            keyring_cls.priority
        except RuntimeError:
            return False
        return True

    all_classes = PlexiglasPlugin._classes
    viable_classes = filter(is_class_viable, all_classes)
    return list(sorted(suppress_exceptions(viable_classes, exceptions=TypeError), key=lambda x: x.priority,
                       reverse=True))
