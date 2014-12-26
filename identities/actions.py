import django.db
from service import (
    actions,
    validators,
)

from protobufs.identity_service_pb2 import IdentityService

from . import (
    containers,
    models,
)


class CreateIdentity(actions.Action):

    type_validators = {
        'identity.user_id': [validators.is_uuid4],
    }

    def _create_identity(self):
        identity = None
        try:
            identity = models.Identity.objects.create(
                user_id=self.request.identity.user_id,
                type=self.request.identity.type,
                first_name=self.request.identity.first_name,
                last_name=self.request.identity.last_name,
                email=self.request.identity.email,
                phone_number=self.request.identity.phone_number,
            )
        except django.db.IntegrityError:
            self.note_error(
                'DUPLICATE',
                ('identity', 'ALREADY_EXISTS'),
            )
        return identity

    def run(self, *args, **kwargs):
        model = self._create_identity()
        if model:
            containers.copy_model_to_container(model, self.response.identity)


class GetIdentity(actions.Action):

    def _get_identity(self):
        parameters = {'type': self.request.type}
        if self.request.type == IdentityService.Containers.Identity.INTERNAL:
            parameters['email'] = self.request.key
        return models.Identity.objects.get_or_none(**parameters)

    def run(self, *args, **kwargs):
        model = self._get_identity()
        if model:
            containers.copy_model_to_container(model, self.response.identity)
        else:
            self.note_error(
                'DOES_NOT_EXIST',
                ('identity', 'identity doesn\'t exist'),
            )


class GetIdentities(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        identities = models.Identity.objects.filter(
            user_id=self.request.user_id,
        )
        for model in identities:
            container = self.response.identities.add()
            containers.copy_model_to_container(model, container)
