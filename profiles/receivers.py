from django.db.models.signals import post_save
from django.dispatch import receiver
from protobufs.services.search.containers import entity_pb2

from services.search import update_entity

from . import models


@receiver(post_save, sender=models.Profile)
def update_search_index_on_profile_update(sender, **kwargs):
    instance = kwargs['instance']
    update_entity(instance.pk, instance.organization_id, entity_pb2.PROFILE)
