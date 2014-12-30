from django.contrib.postgres.fields import HStoreField
from phonenumber_field.modelfields import PhoneNumberField

from common.db import models


class Profile(models.UUIDModel, models.TimestampableModel):

    organization_id = models.UUIDField()
    user_id = models.UUIDField()
    address_id = models.UUIDField()
    team_id = models.UUIDField()
    title = models.CharField(max_length=64)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    cell_phone = PhoneNumberField(null=True)
    work_phone = PhoneNumberField(null=True)
    image_url = models.CharField(max_length=256, null=True)
    location = HStoreField(null=True)
    email = models.EmailField()

    class Meta:
        unique_together = ('organization_id', 'user_id')
