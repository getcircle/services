# import default settings
from . import *  # noqa

from service import settings
settings.MAX_PAGE_SIZE = os.environ.get('MAX_PAGE_SIZE', 10000)
settings.DEFAULT_METRICS_HANDLER = 'service.metrics.log.instance'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'services',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}

METRICS_HANDLER_KWARGS = {'name': 'services.metrics'}
