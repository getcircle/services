import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from protobufs.services.search.containers import entity_pb2
import service.control

from services.token import make_admin_token

from . import models

logger = logging.getLogger(__file__)


@receiver(post_save, sender=models.Post)
def update_search_index_on_post_update(sender, **kwargs):
    instance = kwargs['instance']
    token = make_admin_token(organization_id=instance.organization_id)
    try:
        service.control.call_action(
            service='search',
            action='update_entities',
            client_kwargs={'token': token},
            ids=[str(instance.pk)],
            type=entity_pb2.POST,
        )
    except service.control.CallActionError as e:
        logger.error(e.summary)
