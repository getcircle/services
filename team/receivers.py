from django.db.models.signals import (
    post_delete,
    post_save,
)
from django.dispatch import receiver
from protobufs.services.search.containers import entity_pb2

from services.search import (
    delete_entity,
    update_entity,
)

from . import models


@receiver(post_save, sender=models.Team)
def update_search_index_on_team_update(sender, **kwargs):
    instance = kwargs['instance']
    update_entity(instance.pk, instance.organization_id, entity_pb2.TEAM)


@receiver(post_delete, sender=models.Team)
def delete_entity_on_team_delete(sender, **kwargs):
    instance = kwargs['instance']
    delete_entity(instance.pk, instance.organization_id, entity_pb2.TEAM)
