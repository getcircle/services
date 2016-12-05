# local settings when running a shell in docker

from .docker import *  # NOQA

LOGGING['loggers']['elasticsearch.trace'] = {
    'level': 'INFO',
    'handlers': ['console_generic'],
    'propagate': False,
}
