web: bin/start-pgbouncer gunicorn services.wsgi -c services/gunicorn.py
worker: celery -A services worker -l info
