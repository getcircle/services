"""
Django settings for services project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
import json
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '5rvaf1tsov&kdz!xp-x3785dc0xdmd+gh+#%-nl3ep-!e+ngot'

SECRET_ENCRYPTION_KEY_V1 = 'q5pFzPB9HgB5IUSrgcuyW94aPLJT_jUcegb-jBdAhTQ='
SECRET_ENCRYPTION_KEYS = [
    SECRET_ENCRYPTION_KEY_V1,
]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['api.circlehq.co']


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

    'api',
    'authentication',
    'glossary',
    'group',
    'history',
    'media',
    'notification',
    'onboarding',
    'organizations',
    'profiles',
    'search',
    'sync',
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
    'glossary.server.Server',
    'group.server.Server',
    'history.server.Server',
    'media.server.Server',
    'notification.server.Server',
    'organizations.server.Server',
    'profiles.server.Server',
    'search.server.Server',
    'sync.server.Server',
    'users.server.Server',
]

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'users.backends.GoogleAuthenticationBackend',
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

# TODO setup proper logging
LOGGING = {
    'version': 1,
    'formatters': {
        'generic': {
            'format': '%(name)s %(message)s',
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
        'django': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'gunicorn.error': {
            'level': 'INFO',
            'handlers': ['console_generic'],
            'propagate': True,
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['console_generic'],
            'propagate': False,
        },
        'services': {
            'level': 'INFO',
            'handlers': ['console_generic'],
            'propagate': False,
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
}

# Twilio API Settings
TWILIO_ACCOUNT_SID = "AC952fb40dc6238649d073d9b44d677538"
TWILIO_AUTH_TOKEN = "247a4bc227697c29cec954885b641d51"
TWILIO_PHONE_NUMBER = "+1 415-930-9683"

# TODO what is the downside of doing this?
# Set a TOTP Interval of 2 minutes
USER_SERVICE_TOTP_INTERVAL = 60 * 2

# XXX move to environmental variables
# AWS "services" IAM
AWS_ACCESS_KEY_ID = "AKIAJXKUJANGM6O3Z6ZQ"
AWS_SECRET_ACCESS_KEY = "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"

# AWS SNS Settings
AWS_SNS_PLATFORM_APPLICATION_APNS = ''
AWS_SNS_PLATFORM_APPLICATION_GCM = ''

AWS_S3_MEDIA_BUCKET = 'otterbots-media'

# XXX temporary db cache until we setup memcache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'services.authentication.ServiceTokenAuthentication',
        'services.authentication.OrganizationTokenAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    )
}

# Connect With LinkedIn
LINKEDIN_AUTHORIZATION_URL = 'https://www.linkedin.com/uas/oauth2/authorization'
LINKEDIN_ACCESS_TOKEN_URL = 'https://www.linkedin.com/uas/oauth2/accessToken'
LINKEDIN_CLIENT_ID = '75ob8lid33ecuv'
LINKEDIN_CLIENT_SECRET = 'vZsCybgJMvZ0rPEj'
LINKEDIN_REDIRECT_URI = 'http://localhost:8000/oauth2/linkedin/'
LINKEDIN_SCOPE = 'r_basicprofile r_emailaddress'

# Sign In With Google
GOOGLE_AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_ACCESS_TOKEN_URL = 'https://www.googleapis.com/oauth2/v3/token'
GOOGLE_REVOKE_TOKEN_URL = 'https://accounts.google.com/o/oauth2/revoke'
GOOGLE_CLIENT_ID = '1077014421904-1a697ks3qvtt6975qfqhmed8529en8s2.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'lIjknz85LXHAQGMWM7A8QtPx'
GOOGLE_SCOPE = (
    'https://www.googleapis.com/auth/plus.login '
    'https://www.googleapis.com/auth/plus.profile.emails.read '
    'https://www.google.com/m8/feeds '
)
GOOGLE_REDIRECT_URI = 'http://localhost:8000/oauth2/google/'
GOOGLE_PROFILE_URL = 'https://www.googleapis.com/plus/v1/people/me'

# Google Maps API
GOOGLE_USER_AGENT = 'circlehq-v1.0'
GOOGLE_API_KEY = 'AIzaSyAM0Kl2eU_nyo4OnL529-TEocozCiE_HY8'
GOOGLE_TIMEZONE_ENDPOINT = 'https://maps.googleapis.com/maps/api/timezone/json'

# User Service Settings
USER_SERVICE_STATE_MAX_AGE = 60 * 5  # number of seconds to allow for state token
USER_SERVICE_FORCE_INTERNAL_AUTHENTICATION = ('demo@circlehq.co',)
USER_SERVICE_FORCE_GOOGLE_AUTH = tuple()

# Data Dog API Key
DATADOG_API_KEY = ''

# Metrics Handler
METRICS_HANDLER_KWARGS = {}

CACHEOPS_DEFAULTS = {
    # set default cache to 1 hour
    'timeout': 60*60,
}

CACHEOPS = {
    'glossary.*': {'ops': 'all'},
    'group.*': {'ops': 'all'},
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
