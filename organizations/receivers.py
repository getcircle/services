import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from protobufs.services.search.containers import entity_pb2
import service.control

from services.token import make_admin_token

from . import models

logger = logging.getLogger(__file__)


def _update_entity(primary_key, organization_id, entity_type):
    token = make_admin_token(organization_id=organization_id)
    try:
        service.control.call_action(
            service='search',
            action='update_entities',
            client_kwargs={'token': token},
            ids=[str(primary_key)],
            type=entity_type,
        )
    except service.control.CallActionError as e:
        logger.error(e.summary)


@receiver(post_save, sender=models.Team)
def update_search_index_on_team_update(sender, **kwargs):
    instance = kwargs['instance']
    _update_entity(instance.pk, instance.organization_id, entity_pb2.TEAM)


@receiver(post_save, sender=models.Location)
def update_search_index_on_location_update(sender, **kwargs):
    instance = kwargs['instance']
    _update_entity(instance.pk, instance.organization_id, entity_pb2.LOCATION)
