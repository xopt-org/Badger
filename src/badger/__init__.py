"""Badger: a PyQt5-based GUI application for configuring, running, and
managing optimization routines backed by the Xopt library. This top-level
package exposes the version number and serves as the namespace root for all
Badger sub-modules including the plugin system, database layer, and GUI."""

try:
    from badger._version import __version__
except ImportError:
    __version__ = "0.0.0"
