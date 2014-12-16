from service import (
    actions,
    validators,
)

from . import models


class CreateUser(actions.Action):

    def run(self, *args, **kwargs):
        user = models.User.objects.create()
        self.response.user_id = user.id.hex


class ValidUser(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        self.response.exists = models.User.objects.filter(
            pk=self.request.user_id,
        ).exists()
