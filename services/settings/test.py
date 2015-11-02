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

es_url = urlparse.urlparse(os.environ['SEARCH_SERVICE_ELASTICSEARCH_URL'])
SEARCH_SERVICE_ELASTICSEARCH = {
    'hosts': ['%s:%s' % (es_url.hostname, es_url.port)],
    'timeout': 10,
}
