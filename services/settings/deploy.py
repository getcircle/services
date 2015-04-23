import os
import urlparse

# import default settings
from . import *  # noqa

from service import settings
settings.MAX_PAGE_SIZE = os.environ.get('MAX_PAGE_SIZE', 100)
settings.DEFAULT_METRICS_HANDLER = 'service.metrics.datadog.instance'

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

# NB: Specify 'cacheops' as an installed app only when we define redis
# connection settings
#INSTALLED_APPS = INSTALLED_APPS + ('cacheops',)
#redis_url = urlparse.urlparse(os.environ['REDIS_URL'])
#CACHEOPS_REDIS = {
#    'host': redis_url.hostname,
#    'port': redis_url.port,
#    'db': redis_url.path[1:],
#    'socket_timeout': os.environ.get('CACHEOPS_REDIS_SOCKET_TIMEOUT', 3),
#}

LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '')

DATADOG_API_KEY = os.environ.get('DATADOG_API_KEY', '')
METRICS_HANDLER_KWARGS = {'api_key': DATADOG_API_KEY}
