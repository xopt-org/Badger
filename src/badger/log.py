import logging
from logging.config import dictConfig

from badger.utils import merge_params

logger = logging.getLogger(__name__)


LOG_CONFIG_DEFAULT = {
    "version": 1,
    "formatters": {
        "simple": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {"level": "WARNING", "handlers": ["console"]},
}


# Do not call this function twice within one session
# it will screw up the logging system
def config_log(dict_config=None):
    _config = merge_params(LOG_CONFIG_DEFAULT, dict_config)
    dictConfig(_config)


def set_log_level(level):
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for logger in loggers:
        logger.setLevel(level)
