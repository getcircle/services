from phonenumber_field.modelfields import PhoneNumberField

from common.db import models

import identities as identity_constants


class Identity(models.UUIDModel, models.TimestampableModel):

    first_name = models.CharField(max_length=64, null=True)
    last_name = models.CharField(max_length=64, null=True)
    type = models.PositiveSmallIntegerField(
        choices=identity_constants.IDENTITY_TYPES,
        default=identity_constants.IDENTITY_TYPE_INTERNAL,
    )
    email = models.EmailField()
    phone_number = PhoneNumberField(null=True)
    user_id = models.UUIDField()

    class Meta:
        unique_together = ('type', 'email')
