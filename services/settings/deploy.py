import os
import urlparse

# import default settings
from . import *  # noqa

from service import settings
settings.MAX_PAGE_SIZE = os.environ.get('MAX_PAGE_SIZE', 100)
settings.DEFAULT_METRICS_HANDLER = 'service.metrics.datadog.instance'

DEBUG = False
TEMPLATE_DEBUG = False

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
INSTALLED_APPS = INSTALLED_APPS + (
    'cacheops',
    'raven.contrib.django.raven_compat',
)
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

LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '')

DATADOG_API_KEY = os.environ.get('DATADOG_API_KEY', '')
METRICS_HANDLER_KWARGS = {'api_key': DATADOG_API_KEY}

_force_google = os.environ.get('USER_SERVICE_FORCE_GOOGLE_AUTH')
if isinstance(_force_google, basestring):
    _force_google = _force_google.split(',')
USER_SERVICE_FORCE_GOOGLE_AUTH = (
    _force_google or USER_SERVICE_FORCE_GOOGLE_AUTH
)

_user_service_allowed_redirect_uris = os.environ.get('USER_SERVICE_ALLOWED_REDIRECT_URIS')
if isinstance(_user_service_allowed_redirect_uris, basestring):
    _user_service_allowed_redirect_uris = _user_service_allowed_redirect_uris.split(',')
USER_SERVICE_ALLOWED_REDIRECT_URIS = (
    _user_service_allowed_redirect_uris or USER_SERVICE_ALLOWED_REDIRECT_URIS
)

_organization_service_allowed_redirect_uris = os.environ.get(
    'ORGANIZATION_SERVICE_ALLOWED_REDIRECT_URIS',
)
if isinstance(_organization_service_allowed_redirect_uris, basestring):
    _organization_service_allowed_redirect_uris = (
        _organization_service_allowed_redirect_uris.split(',')
    )
ORGANIZATION_SERVICE_ALLOWED_REDIRECT_URIS = (
    _organization_service_allowed_redirect_uris or ORGANIZATION_SERVICE_ALLOWED_REDIRECT_URIS
)

AWS_SNS_PLATFORM_APPLICATION_APNS = os.environ.get('AWS_SNS_PLATFORM_APPLICATION_APNS')
AWS_SNS_PLATFORM_APPLICATION_GCM = os.environ.get('AWS_SNS_PLATFORM_APPLICATION_GCM')

CORS_ORIGIN_WHITELIST = tuple(os.environ.get('CORS_ORIGIN_WHITELIST', '').split(','))

RAVEN_CONFIG = {
    'dsn': os.environ.get('SENTRY_DSN'),
}

# XXX default to api.lunohq.com in the future
HOSTNAME = os.environ.get('HOSTNAME', 'api.circlehq.co')

# Disable the browsable API
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'services.authentication.ServiceTokenAuthentication',
        'services.authentication.OrganizationTokenAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
}

# XXX default to api.lunohq.com in the future
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'api.circlehq.co').split(',')

STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

AWS_S3_MEDIA_BUCKET = os.environ.get('AWS_S3_MEDIA_BUCKET', AWS_S3_MEDIA_BUCKET)

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', GOOGLE_CLIENT_ID)
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', GOOGLE_CLIENT_SECRET)
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', GOOGLE_API_KEY)

AUTH_SUCCESS_REDIRECT_URI = os.environ.get('AUTH_SUCCESS_REDIRECT_URI', AUTH_SUCCESS_REDIRECT_URI)
