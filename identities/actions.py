import django.db
import service

import identities as identity_constants
from . import (
    containers,
    models,
)


class IdentityType(service.StringType):

    def __init__(self, *args, **kwargs):
        super(IdentityType, self).__init__(*args, **kwargs)
        self.choices = identity_constants.IDENTITY_TYPE_TO_NAME_MAP.keys()

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
    type = IdentityType(required=True)
    email = service.EmailType(required=True)
    phone_number = service.PhoneNumberType()

    identity = service.ContainerType(containers.IdentityContainer)

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
        model = self._create_identity()
        if model:
            self.identity = containers.IdentityContainer.from_model(model)

    class Options:
        roles = {service.public: service.whitelist('identity')}


class GetIdentity(service.Action):

    type = IdentityType(required=True)
    key = service.StringType(required=True)

    identity = service.ContainerType(containers.IdentityContainer)

    def validate_key(self, value, context=None):
        if self.type == identity_constants.IDENTITY_TYPE_INTERNAL:
            email_type = service.EmailType()
            email_type.validate(value)

    def _get_identity(self):
        parameters = {'type': self.type}
        if self.type == identity_constants.IDENTITY_TYPE_INTERNAL:
            parameters['email'] = self.key
        return models.Identity.objects.get_or_none(**parameters)

    def run(self, *args, **kwargs):
        model = self._get_identity()
        if model:
            self.identity = containers.IdentityContainer.from_model(model)

    class Options:
        roles = {service.public: service.whitelist('identity')}
