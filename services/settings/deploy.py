import os
import urlparse

# import default settings
from . import *

if 'DATABASE_URL' not in os.environ:
    raise Exception('"DATABASE_URL" environmental variable required')

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
