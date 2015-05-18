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

# NB: Specify 'cacheops' as an installed app only when we define redis
# connection settings
INSTALLED_APPS = INSTALLED_APPS + ('cacheops',)
CACHEOPS_REDIS = {
    'host': 'localhost',
    'port': 6379,
    'db': 1,
    'socket_timeout': 3,
}

METRICS_HANDLER_KWARGS = {'name': 'services.metrics'}

CORS_ORIGIN_ALLOW_ALL = True
