import django.db
import service

import identities as identity_constants
from . import models


class IdentityType(service.StringType):

    def to_native(self, value, context=None):
        if isinstance(value, basestring):
            value = identity_constants.IDENTITY_NAME_TO_TYPE_MAP[value]
        return value

    def to_primitive(self, value, context=None):
        return identity_constants.IDENTITY_TYPE_TO_NAME_MAP[value]


class CreateIdentity(service.Action):

    # TODO add validation for user_id
    user_id = service.StringType(required=True)
    first_name = service.StringType(required=True)
    last_name = service.StringType(required=True)
    type = IdentityType(
        required=True,
        choices=identity_constants.IDENTITY_TYPE_TO_NAME_MAP.keys(),
    )
    email = service.EmailType(required=True)
    phone_number = service.PhoneNumberType()

    def _create_identity(self):
        identity = None
        try:
            identity = models.Identity.objects.create(
                user_id=self.user_id,
                type=self.type,
                first_name=self.first_name,
                last_name=self.last_name,
                email=self.email,
                phone_number=self.phone_number,
            )
        except django.db.IntegrityError:
            pass
        return identity

    def run(self, *args, **kwargs):
        return self._create_identity()
