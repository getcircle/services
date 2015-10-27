from django.db.models.signals import post_save
from django.dispatch import receiver

from .tasks import update_index_for_model


@receiver(post_save)
def update_model_index(sender, **kwargs):
    instance = kwargs['instance']
    update_index_for_model.delay(
        instance._meta.app_label,
        instance._meta.model_name,
        str(instance.pk),
    )
