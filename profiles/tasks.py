import logging
import time

from celery import group

from services.celery import app

from .models import SyncSettings
from .sync.providers import okta

logger = logging.getLogger(__name__)


@app.task
def sync_all():
    start = time.time()
    logger.info('starting profile sync for registered organizations')
    organization_ids = SyncSettings.objects.all().values_list('organization_id', flat=True)
    result = group(
        sync_organization.s(str(organization_id)) for organization_id in organization_ids
    )()
    result.get()
    end = time.time()
    logger.info('completed syncing %d organizations (%d secs)', len(organization_ids), end - start)


@app.task
def sync_organization(organization_id):
    settings = SyncSettings.objects.get(pk=organization_id)
    okta.sync(settings)
