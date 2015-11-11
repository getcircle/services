import os
import urlparse

# import default settings
from . import *  # noqa
from ._utils import _get_delimited_setting_from_environment

from service import settings
settings.MAX_PAGE_SIZE = os.environ.get('MAX_PAGE_SIZE', 100)
settings.DEFAULT_METRICS_HANDLER = 'service.metrics.datadog.instance'
settings.LOG_REQUEST_AND_RESPONSE = int(os.environ.get('SERVICE_LOG_REQUEST_AND_RESPONSE', 1))

DEBUG = False
TEMPLATE_DEBUG = False

database_url = urlparse.urlparse(os.environ['DATABASE_URL'])
conn_max_age = os.environ.get('DATABASE_CONN_MAX_AGE', '')
if conn_max_age.isdigit():
    conn_max_age = int(conn_max_age)
else:
    conn_max_age = None

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': database_url.path[1:],
        'USER': database_url.username,
        'PASSWORD': database_url.password,
        'HOST': database_url.hostname,
        'PORT': database_url.port,
        'CONN_MAX_AGE': conn_max_age,
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

BROKER_URL = 'redis://%s:%s/3' % (redis_url.hostname, redis_url.port)

GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '')

DATADOG_API_KEY = os.environ.get('DATADOG_API_KEY', '')
METRICS_HANDLER_KWARGS = {'api_key': DATADOG_API_KEY}

USER_SERVICE_FORCE_GOOGLE_AUTH = _get_delimited_setting_from_environment(
    'USER_SERVICE_FORCE_GOOGLE_AUTH',
    USER_SERVICE_FORCE_GOOGLE_AUTH,
)
USER_SERVICE_FORCE_INTERNAL_AUTH = _get_delimited_setting_from_environment(
    'USER_SERVICE_FORCE_INTERNAL_AUTH',
    USER_SERVICE_FORCE_INTERNAL_AUTH,
)
USER_SERVICE_FORCE_DOMAIN_INTERNAL_AUTH = _get_delimited_setting_from_environment(
    'USER_SERVICE_FORCE_DOMAIN_INTERNAL_AUTH',
    USER_SERVICE_FORCE_DOMAIN_INTERNAL_AUTH,
)
USER_SERVICE_SAML_AUTH_SUCCESS_REDIRECT_URI = os.environ.get(
    'USER_SERVICE_SAML_AUTH_SUCCESS_REDIRECT_URI',
    USER_SERVICE_SAML_AUTH_SUCCESS_REDIRECT_URI,
)
USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST = os.environ.get(
    'USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST',
    USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST,
)

AWS_ACCESS_KEY_ID = os.environ.get('SERVICES_AWS_ACCESS_KEY_ID', AWS_ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY = os.environ.get('SERVICES_AWS_SECRET_ACCESS_KEY', AWS_SECRET_ACCESS_KEY)

AWS_SNS_PLATFORM_APPLICATION_APNS = os.environ.get('AWS_SNS_PLATFORM_APPLICATION_APNS')
AWS_SNS_PLATFORM_APPLICATION_GCM = os.environ.get('AWS_SNS_PLATFORM_APPLICATION_GCM')
AWS_SNS_KWARGS = {
    'aws_access_key_id': AWS_ACCESS_KEY_ID,
    'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
    'region_name': os.environ.get('AWS_SNS_REGION_NAME', 'us-east-1'),
}
AWS_SNS_TOPIC_REQUEST_ACCESS = os.environ.get(
    'AWS_SNS_TOPIC_REQUEST_ACCESS',
    AWS_SNS_TOPIC_REQUEST_ACCESS,
)
AWS_SNS_TOPIC_NO_SEARCH_RESULTS = os.environ.get(
    'AWS_SNS_TOPIC_NO_SEARCH_RESULTS',
    AWS_SNS_TOPIC_NO_SEARCH_RESULTS,
)

RAVEN_CONFIG = {
    'dsn': os.environ.get('SENTRY_DSN'),
}

# XXX default to api.lunohq.com in the future
SERVICES_HOSTNAME = os.environ.get('SERVICES_HOSTNAME', 'api.circlehq.co')
FRONTEND_URL = os.environ.get('FRONTEND_URL', FRONTEND_URL)

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
ALLOWED_HOSTS = _get_delimited_setting_from_environment(
    'ALLOWED_HOSTS',
    ALLOWED_HOSTS,
)

STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', STRIPE_API_KEY)

AWS_S3_MEDIA_BUCKET = os.environ.get('AWS_S3_MEDIA_BUCKET', AWS_S3_MEDIA_BUCKET)
AWS_S3_FILE_BUCKET = os.environ.get('AWS_S3_FILE_BUCKET', AWS_S3_FILE_BUCKET)

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', GOOGLE_CLIENT_ID)
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', GOOGLE_CLIENT_SECRET)
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', GOOGLE_API_KEY)

SECRET_KEY = os.environ['SECRET_KEY']
SECRET_ENCRYPTION_KEYS = _get_delimited_setting_from_environment(
    'SECRET_ENCRYPTION_KEYS',
    SECRET_ENCRYPTION_KEYS,
)

SEARCH_SERVICE_ELASTICSEARCH_URL = os.environ.get('SEARCH_SERVICE_ELASTICSEARCH_URL')
if SEARCH_SERVICE_ELASTICSEARCH_URL:
    SEARCH_SERVICE_ELASTICSEARCH = {
        'hosts': [SEARCH_SERVICE_ELASTICSEARCH_URL],
        'timeout': 10,
    }

FEATURE_SERVICE_POSTS_ENABLED_ORGANIZATIONS = _get_delimited_setting_from_environment(
    'FEATURE_SERVICE_POSTS_ENABLED_ORGANIZATIONS',
    FEATURE_SERVICE_POSTS_ENABLED_ORGANIZATIONS,
)

SEARCH_SERVICE_SEARCH_V2_ENABLED_ORGANIZATION_IDS = _get_delimited_setting_from_environment(
    'SEARCH_SERVICE_SEARCH_V2_ENABLED_ORGANIZATION_IDS',
    SEARCH_SERVICE_SEARCH_V2_ENABLED_ORGANIZATION_IDS,
)
