web: gunicorn services.wsgi -c services/gunicorn.py
worker: celery -A services worker -l info
scheduler: celery -A services beat -l info
