from .docker import *  # NOQA

CACHEOPS_FAKE = True
settings.DEFAULT_METRICS_HANDLER = 'service.metrics.local.instance'

LOGGING['handlers']['console'] = {
    'class': 'logging.NullHandler',
}
LOGGING['handlers']['console_generic'] = {
    'class': 'logging.NullHandler',
}

CELERY_ALWAYS_EAGER = True

SEARCH_SERVICE_ELASTICSEARCH = None
