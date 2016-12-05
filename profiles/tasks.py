import logging
import time

from celery import chord

from services.celery import app

from .models import SyncSettings
from .sync.providers import okta

logger = logging.getLogger(__name__)

TIME_LIMIT = 60 * 5


@app.task
def sync_all():
    """Trigger syncing for all registered organizations"""
    start = time.time()
    logger.info('starting profile sync for registered organizations')
    organization_ids = SyncSettings.objects.all().values_list('organization_id', flat=True)
    subtasks = [sync_organization.s(str(organization_id)) for organization_id in organization_ids]
    chord(subtasks, report_sync_stats.si(start, len(organization_ids))).delay()


@app.task(time_limit=TIME_LIMIT, soft_time_limit=TIME_LIMIT, ignore_result=False)
def sync_organization(organization_id):
    settings = SyncSettings.objects.get(pk=organization_id)
    okta.sync(settings)


@app.task
def report_sync_stats(start, number):
    end = time.time()
    logger.info('completed syncing %d organizations (%d secs)', number, end - start)
