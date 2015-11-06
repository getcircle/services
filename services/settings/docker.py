# local settings when running in docker
import os
import urlparse

from .local import *  # NOQA
from ._utils import _get_delimited_setting_from_environment

database_url = urlparse.urlparse(os.environ['DATABASE_URL'])

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': database_url.path[1:],
        'USER': database_url.username,
        'PASSWORD': database_url.password,
        'HOST': database_url.hostname,
        'PORT': database_url.port,
    }
}

redis_url = urlparse.urlparse(os.environ['REDIS_URL'])
CACHEOPS_REDIS = {
    'host': redis_url.hostname,
    'port': redis_url.port,
    'db': redis_url.path[1:],
    'socket_timeout': os.environ.get('CACHEOPS_REDIS_SOCKET_TIMEOUT', 3),
}

SERVICES_REDIS = {
    'host': redis_url.hostname,
    'port': redis_url.port,
    'db': 2,
    'socket_timeout': os.environ.get('SERVICES_REDIS_SOCKET_TIMEOUT', 3),
}

BROKER_URL = 'redis://%s:%s/3' % (redis_url.hostname, redis_url.port)

es_url = urlparse.urlparse(os.environ['SEARCH_SERVICE_ELASTICSEARCH_URL'])
SEARCH_SERVICE_ELASTICSEARCH = {
    'hosts': ['%s:%s' % (es_url.hostname, es_url.port)],
    'timeout': 10,
}

FEATURE_SERVICE_POSTS_ENABLED_ORGANIZATIONS = _get_delimited_setting_from_environment(
    'FEATURE_SERVICE_POSTS_ENABLED_ORGANIZATIONS',
    FEATURE_SERVICE_POSTS_ENABLED_ORGANIZATIONS,
)
