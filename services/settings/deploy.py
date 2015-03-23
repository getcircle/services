import os
import urlparse

# import default settings
from . import *  # noqa

from service import settings
settings.MAX_PAGE_SIZE = os.environ.get('MAX_PAGE_SIZE', 100)
settings.DEFAULT_METRICS_HANDLER = 'service.metrics.datadog.instance'

url = urlparse.urlparse(os.environ['DATABASE_URL'])
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': url.path[1:],
        'USER': url.username,
        'PASSWORD': url.password,
        'HOST': url.hostname,
        'PORT': url.port,
    }
}

LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI', '')

DATADOG_API_KEY = os.environ.get('DATADOG_API_KEY', '')
METRICS_HANDLER_KWARGS = {'api_key': settings.DATADOG_API_KEY}
