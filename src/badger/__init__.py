import os

_DEFAULT_NUM_THREADS = "4"

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, _DEFAULT_NUM_THREADS)

try:
    from badger._version import __version__
except ImportError:
    __version__ = "0.0.0"
