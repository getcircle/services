from phonenumber_field.modelfields import PhoneNumberField

from common.db import models
from protobufs.identity_service_pb2 import IdentityService


class Identity(models.UUIDModel, models.TimestampableModel):

    first_name = models.CharField(max_length=64, null=True)
    last_name = models.CharField(max_length=64, null=True)
    type = models.PositiveSmallIntegerField(
        choices=(
            (IdentityService.Containers.Identity.INTERNAL, 'INTERNAL'),
        ),
        default=IdentityService.Containers.Identity.INTERNAL,
    )
    email = models.EmailField()
    phone_number = PhoneNumberField(null=True)
    user_id = models.UUIDField()

    class Meta:
        unique_together = ('type', 'email')
