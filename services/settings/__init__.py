"""
Django settings for services project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
import json
import os
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

ALLOWED_HOSTS = ['.local.lunohq.com', 'services']

SERVICES_HOSTNAME = 'api.local.lunohq.com:8000'
FRONTEND_URL = 'http://local.lunohq.com:3000'
AUTHENTICATION_TOKEN_COOKIE_BASE_DOMAIN = 'local.lunohq.com'
# max age of the cookie in seconds
AUTHENTICATION_TOKEN_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
AUTHENTICATION_TOKEN_COOKIE_SECURE = False

SECRET_KEY = '5rvaf1tsov&kdz!xp-x3785dc0xdmd+gh+#%-nl3ep-!e+ngot'
SECRET_ENCRYPTION_KEY_V1 = 'q5pFzPB9HgB5IUSrgcuyW94aPLJT_jUcegb-jBdAhTQ='
SECRET_ENCRYPTION_KEYS = [
    SECRET_ENCRYPTION_KEY_V1,
]

# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.postgres',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django_extensions',

    'corsheaders',
    'rest_framework',
    'timezone_field',
    'watson',
    'mptt',

    'services',

    'feature',
    'file',
    'group',
    'history',
    'hooks',
    'media',
    'notification',
    'onboarding',
    'organizations',
    'post',
    'profiles',
    'search',
    'team',
    'users',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'services.middleware.gzip.GZipMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'services.urls'

WSGI_APPLICATION = 'services.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = 'static'

LOCALIZED_SERVICES = [
    'feature.server.Server',
    'file.server.Server',
    'history.server.Server',
    'media.server.Server',
    'notification.server.Server',
    'organizations.server.Server',
    'payment.server.Server',
    'post.server.Server',
    'profiles.server.Server',
    'search.server.Server',
    'team.server.Server',
    'users.server.Server',
]

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = (
    'users.backends.UserBackend',
    'users.backends.GoogleAuthenticationBackend',
    'users.backends.OktaAuthenticationBackend',
)

SESSION_SERIALIZER = 'services.serializers.JSONSerializer'

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
]

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
)

TEST_RUNNER = 'services.test.runner.ServicesTestSuiteRunner'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['console_generic'],
    },
    'formatters': {
        'generic': {
            'format': '%(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
        'console_generic': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'generic',
        },
    },
    'loggers': {
        'py.warnings': {
            'handlers': ['console_generic'],
        },
    },
}

# Twilio API Settings
TWILIO_ACCOUNT_SID = "AC952fb40dc6238649d073d9b44d677538"
TWILIO_AUTH_TOKEN = "247a4bc227697c29cec954885b641d51"
TWILIO_PHONE_NUMBER = "+1 415-930-9683"

# Set a TOTP Interval of 2 minutes
USER_SERVICE_TOTP_INTERVAL = 60 * 2

AWS_ACCESS_KEY_ID = 'AKIAIFWNDY77BUE3MKKA'
AWS_SECRET_ACCESS_KEY = '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'

AWS_REGION_NAME = 'us-west-2'
AWS_HOSTED_ZONE_ID = 'Z2RUM0QYIALWAH'
AWS_ALIAS_HOSTED_ZONE_ID = 'Z1H1FL5HABSF5'
AWS_ALIAS_TARGET = 'dualstack.2e964c47f614473ba0629f17a5670682-65387849.us-west-2.elb.amazonaws.com.'
AWS_SES_INBOUND_ENDPOINT = 'inbound-smtp.us-west-2.amazonaws.com'

# AWS SNS Settings
AWS_SNS_PLATFORM_APPLICATION_APNS = ''
AWS_SNS_PLATFORM_APPLICATION_GCM = ''
AWS_SNS_KWARGS = {
    'aws_access_key_id': AWS_ACCESS_KEY_ID,
    'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
    'region_name': 'us-west-2',
}
AWS_SNS_TOPIC_REQUEST_ACCESS = 'arn:aws:sns:us-west-2:487220619225:dev-lunohq-accessRequest-Topic-1GNW0ZXVZ80OA'
AWS_SNS_TOPIC_NO_SEARCH_RESULTS = 'arn:aws:sns:us-west-2:487220619225:dev-lunohq-noSearchResults-Topic-4UFRYJPVYA6W'

AWS_S3_MEDIA_BUCKET = 'dev-lunohq-media'
AWS_S3_FILE_BUCKET = 'dev-lunohq-files'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'services.authentication.ServiceTokenAuthentication',
        'services.authentication.ServiceTokenCookieAuthentication',
    )
}

# Sign In With Google
GOOGLE_AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_ACCESS_TOKEN_URL = 'https://www.googleapis.com/oauth2/v3/token'
GOOGLE_REVOKE_TOKEN_URL = 'https://accounts.google.com/o/oauth2/revoke'
GOOGLE_CLIENT_ID = '1090169577912-57r89ml43udqthb050v57kim3vddlrvu.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'nSWzmajmO9vjDuyebn65Y0l9'
GOOGLE_SCOPE = 'profile email'
GOOGLE_REDIRECT_URI = 'http://api.local.lunohq.com:8000/user/auth/oauth2/google/'
GOOGLE_USER_INFO = 'https://www.googleapis.com/oauth2/v2/userinfo'

# Google Maps API
GOOGLE_USER_AGENT = 'lunohq-v1.0'
GOOGLE_API_KEY = 'AIzaSyBvkJcNxomtXZeLnN4PwB3Vz90MObqDO-E'
GOOGLE_TIMEZONE_ENDPOINT = 'https://maps.googleapis.com/maps/api/timezone/json'
GOOGLE_GEOCODING_ENDPOINT = 'https://maps.googleapis.com/maps/api/geocode/json'

# User Service Settings
USER_SERVICE_STATE_MAX_AGE = 60 * 5  # number of seconds to allow for state token
USER_SERVICE_FORCE_GOOGLE_AUTH = tuple()
USER_SERVICE_FORCE_INTERNAL_AUTH = tuple()
USER_SERVICE_FORCE_DOMAIN_INTERNAL_AUTH = tuple()
USER_SERVICE_SAML_AUTH_SUCCESS_REDIRECT_URI = 'http://local.lunohq.com:3000/auth'
USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST = tuple(
    '^(https?://)?([A-Za-z0-9\-_]+\.)?(\w+\.)?(\w+\.)?lunohq\.com/auth$',
)

# Data Dog API Key
DATADOG_API_KEY = ''

# Metrics Handler
METRICS_HANDLER_KWARGS = {}

CACHEOPS_DEFAULTS = {
    # set default cache to 1 hour
    'timeout': 60*60,
}

CACHEOPS = {
    'notification.*': {'ops': 'all'},
    'organizations.*': {'ops': 'all'},
    'profiles.*': {'ops': 'all'},
    'organizations.reportingstructure': {},
    '*.*': {},
}

# Google Admin SDK
GOOGLE_ADMIN_SDK_JSON_KEY = json.loads(os.environ.get('GOOGLE_ADMIN_SDK_JSON_KEY', '{}'))

PHONENUMBER_DEFAULT_REGION = 'US'

# Cache timeout in seconds
CACHEOPS_FUNC_IS_GOOGLE_DOMAIN_TIMEOUT = 3600

SHELL_PLUS_POST_IMPORTS = (
    'service.control',
    ('services.token', 'make_admin_token'),
    ('services.bootstrap', 'Bootstrap'),
    ('services.test.utils', 'setup_shell'),
)

STRIPE_API_KEY = 'sk_test_egjGFfpd8I06ZN05Xbh4HZQI'

CORS_ORIGIN_REGEX_WHITELIST = ('^(https?://)?([A-Za-z0-9\-_]+\.)?(\w+\.)?(\w+\.)?lunohq\.com$',)

CELERY_TASK_SERIALIZER = 'msgpack'
CELERY_RESULT_SERIALIZER = 'msgpack'
CELERY_ACCEPT_CONTENT = ['msgpack']
CELERYD_TASK_TIME_LIMIT = 30
CELERYD_TASK_SOFT_TIME_LIMIT = 15
CELERY_DISABLE_RATE_LIMITS = True
CELERYD_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(name)s %(message)s'

SEARCH_SERVICE_ELASTICSEARCH = None

TESTS_TEARDOWN_ES = False

EMAIL_HOOK_SECRET_KEY_V1 = '$*57y+7k9w4@^t@75_g2wl=kix1ws91g&@cc#x6tin#uko396@'
EMAIL_HOOK_SECRET_KEYS = [
    EMAIL_HOOK_SECRET_KEY_V1,
]
EMAIL_HOOK_UNPROCESSED_KEY_PREFIX = 'unprocessed'
EMAIL_HOOK_PROCESSED_KEY_PREFIX = 'processed'
EMAIL_HOOK_S3_BUCKET = 'dev-lunohq-emails'
EMAIL_SES_REGION = 'us-west-2'
EMAIL_HOOK_NOTIFICATION_FROM_ADDRESS = 'notifications@lunohq.com'

SILENCED_SYSTEM_CHECKS = [
    'auth.W004',
]

SLACK_AUTHORIZATION_URL = 'https://slack.com/oauth/authorize'
SLACK_TOKEN_URL = 'https://slack.com/api/oauth.access'
SLACK_CLIENT_ID = '22618016311.22622327954'
SLACK_CLIENT_SECRET = '261102011defd0347802cb4d6cc5c592'
SLACK_SLASH_COMMANDS_TOKEN = 'BpiiPNwSC0EnisQT6PUSF1oe'
SLACK_SCOPE = 'commands channels:history users:read'
