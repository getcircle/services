import os
import urlparse

# import default settings
from . import *  # noqa

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

LINKEDIN_REDIRECT_URI = 'http://staging.otterbots.net/oauth2/linkedin/'
