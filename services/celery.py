from __future__ import absolute_import

import os

from celery import (
    Celery,
    signals,
)

from .bootstrap import Bootstrap

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'services.settings')

from django.conf import settings

app = Celery('celery')

app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


def on_worker_process_init(*args, **kwargs):
    Bootstrap.bootstrap()


signals.worker_process_init.connect(on_worker_process_init, dispatch_uid='bootstrap')
