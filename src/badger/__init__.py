"""Top-level Badger package. Exposes the version number and serves as
the namespace root for the plugin system, database, and GUI."""

try:
    from badger._version import __version__
except ImportError:
    __version__ = "0.0.0"
