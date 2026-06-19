"""Top-level Badger package. Exposes the version number and serves as
the namespace root for the plugin system, database, and GUI. 
Also sets a cap on the library threads to 4 by default, since
libraries auto-detect all available cores and spawn that many threads.
This prevents performance degradation on high-core-count for
typical BO workloads. Does not override user-set environment variables."""

import os

_DEFAULT_NUM_THREADS = "4"

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, _DEFAULT_NUM_THREADS)

try:
    from badger._version import __version__
except ImportError:
    __version__ = "0.0.0"
