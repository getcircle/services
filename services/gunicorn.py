# Gunicorn config

bind = "0.0.0.0:5000"
workers = 4
worker_class = 'gevent'
accesslog = '-'
errorlog = '-'
loglevel = 'info'
preload_app = True
