# Gunicorn config
import os

bind = "0.0.0.0:%s" % (os.environ.get('PORT', '5000'),)
workers = os.environ.get('GUNICORN_WORKERS', 2)
worker_class = 'gevent'
accesslog = '-'
errorlog = '-'
loglevel = 'info'
