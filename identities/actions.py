import django.db
from service import (
    actions,
    validators,
)

import identities as identity_constants
from . import (
    containers,
    models,
)


class CreateIdentity(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    def _create_identity(self):
        identity = None
        try:
            identity = models.Identity.objects.create(
                user_id=self.request.user_id,
                type=self.request.type,
                first_name=self.request.first_name,
                last_name=self.request.last_name,
                email=self.request.email,
                phone_number=self.request.phone_number,
            )
        except django.db.IntegrityError:
            pass
        return identity

    def run(self, *args, **kwargs):
        model = self._create_identity()
        if model:
            containers.copy_model_to_identity(model, self.response.identity)


class GetIdentity(actions.Action):

    def _get_identity(self):
        parameters = {'type': self.request.type}
        if self.request.type == identity_constants.IDENTITY_TYPE_INTERNAL:
            parameters['email'] = self.request.key
        return models.Identity.objects.get_or_none(**parameters)

    def run(self, *args, **kwargs):
        model = self._get_identity()
        if model:
            containers.copy_model_to_identity(model, self.response.identity)
