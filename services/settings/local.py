# import default settings
from . import *  # noqa

from service import settings
settings.MAX_PAGE_SIZE = os.environ.get('MAX_PAGE_SIZE', 10000)
settings.DEFAULT_METRICS_HANDLER = 'service.metrics.log.instance'

DEBUG = True
TEMPLATE_DEBUG = True

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

DATABASES = {
    'default': {
        'ENGINE': 'django_postgrespool',
        'NAME': 'services',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
        'CONN_MAX_AGE': None,
    }
}

DATABASE_POOL_ARGS = {
    'max_overflow': 10,
    'pool_size': 5,
    'recycle': 300,
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

SERVICES_REDIS = {
    'host': 'localhost',
    'port': 6379,
    'db': 2,
    'socket_timeout': 3,
}

METRICS_HANDLER_KWARGS = {'name': 'services.metrics'}

CORS_ORIGIN_WHITELIST = tuple()
CORS_ORIGIN_REGEX_WHITELIST = ('^(https?://)?(\w+\.)?lunohq\.com(:\d+)?$',)
USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST = (
    '^(https?://)?(\w+\.)?(\w+\.)?(\w+\.)?lunohq\.com(:\d+)?/auth$',
)

GOOGLE_ADMIN_SDK_JSON_KEY = {
    u'client_email': u'1077014421904-v3q3sd1e8n0fq6bgchfv7qul4k9135ur@developer.gserviceaccount.com',
    u'client_id': u'1077014421904-v3q3sd1e8n0fq6bgchfv7qul4k9135ur.apps.googleusercontent.com',
    u'private_key': u'-----BEGIN PRIVATE KEY-----\nMIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAKVBrJWneoiq2FOe\n0oJxfMe6Rc90itSMB3aWl2dCQtSj7J5jw+Lkuuy+8Ck18xJeKt5raOPqEeIRpniH\nKLTlfS/HOt2EYLa23zJHiKCTKld0SjaWqdsdUcCR/cvjU4XdkZBEsIQu1v60o85G\nMBjAqxT0+bzJ+/epiIT5MRw8AqLFAgMBAAECgYAWFDQuunWQlOLaKToO24LEXIq/\nMN7rjtngajZIQX4UUuJmNwYQ5mZjAw+rMd4L8jDgDpGxAbDp91m6eLRjltWmuYrf\nfx/KQ+xFPjz54XN67wtj6KXEnGD17B4kfqmfiV1FxCYujzCGzZZiYR7axSoJSLHW\nNim4qVlfqNQCV95KAQJBANG4KY5x9fJiojUm2AMfXQ03+q2CVhuY+z4qr92g/Mzq\n3Rar38OXoLIRxlVAYgVJCOpMH7aBfthEz035H5bp6CUCQQDJuaNpnYzZ0GFz+A8C\n9p4saYIUJHEt/87iu9Gemp0XwujvN+dF97yPOYCHh6IIE9qcEhqtvDs2e3brjMx3\nO/4hAkAv1+qrE3Z/aF8G7yiidbo9tMKcaLqKKzlN8mESl5J0kTQE4wr2TRYc6Y8s\njbaO7B17jghCE4LDhdchO68oN459AkEAqe9p2yovIrqprhE1TDDHdPB49VDxy2dp\nOJYyc2ManY7DveohOU8GmL0/Km03MYjQK5QQx3T/iNkfiDU3deajIQJACVWyBwpC\nRa0IFvJNk/+ySAFAnr+Z6mor9QzJbsGr0sO0msLOYM1ZbscC0HEq6ujnJbUC/f9u\n3quF8OnrJ1HGWw==\n-----END PRIVATE KEY-----\n',
    u'private_key_id': u'b34aaf973f595b3edce5029f2a1f7fd1ef8a3388',
    u'type': u'service_account',
}

AWS_SNS_PLATFORM_APPLICATION_APNS = 'arn:aws:sns:us-east-1:487220619225:app/APNS_SANDBOX/Circle-Dev'
AWS_SNS_PLATFORM_APPLICATION_GCM = 'arn:aws:sns:us-east-1:487220619225:app/GCM/Circle-Dev'
