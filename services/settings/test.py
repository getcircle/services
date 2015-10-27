from .local import *  # NOQA

CACHEOPS_FAKE = True
settings.DEFAULT_METRICS_HANDLER = 'service.metrics.local.instance'

LOGGING['handlers']['console'] = {
    'class': 'logging.NullHandler',
}
LOGGING['handlers']['console_generic'] = {
    'class': 'logging.NullHandler',
}

CELERY_ALWAYS_EAGER = True

INSTALLED_APPS = INSTALLED_APPS + (
    # register search test models
    'search.tests',
)
