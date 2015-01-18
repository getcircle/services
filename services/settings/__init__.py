"""
Django settings for services project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '5rvaf1tsov&kdz!xp-x3785dc0xdmd+gh+#%-nl3ep-!e+ngot'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django_extensions',

    'rest_framework',
    'rest_framework.authtoken',

    'landing',
    'media',
    'notes',
    'onboarding',
    'organizations',
    'profiles',
    'users',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
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


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

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
    'landing.server.Server',
    'media.server.Server',
    'notes.server.Server',
    'organizations.server.Server',
    'profiles.server.Server',
    'users.server.Server',
]

AUTH_USER_MODEL = 'users.User'

SESSION_SERIALIZER = 'services.serializers.JSONSerializer'

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    )
}

TEST_RUNNER = 'services.test.runner.ServicesTestSuiteRunner'

# TODO setup proper logging
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    }

}

# Twilio API Settings
TWILIO_ACCOUNT_SID = "AC952fb40dc6238649d073d9b44d677538"
TWILIO_AUTH_TOKEN = "247a4bc227697c29cec954885b641d51"
TWILIO_PHONE_NUMBER = "+1 415-930-9683"

# TODO what is the downside of doing this?
# Set a TOTP Interval of 2 minutes
USER_SERVICE_TOTP_INTERVAL = 60 * 2

# AWS "services" IAM
AWS_ACCESS_KEY_ID = "AKIAJXKUJANGM6O3Z6ZQ"
AWS_SECRET_ACCESS_KEY = "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"

AWS_S3_MEDIA_BUCKET = 'otterbots-media'

# XXX temporary db cache until we setup memcache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache',
    }
}
