from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from service import (
    actions,
    validators,
)
import service.control

from . import (
    containers,
    models,
)


def validate_new_password_min_length(value):
    return False if len(value) < 6 else True


def validate_new_password_max_length(value):
    return False if len(value) > 24 else True


class CreateUser(actions.Action):

    field_validators = {
        'password': {
            validate_new_password_min_length: 'INVALID_MIN_LENGTH',
            validate_new_password_max_length: 'INVALID_MAX_LENGTH',
        }
    }

    def run(self, *args, **kwargs):
        user = models.User.objects.create_user(
            primary_email=self.request.identity.email,
            password=self.request.password,
        )

        self.request.identity.user_id = user.id.hex
        client = service.control.Client(
            'identity',
            token=self.token,
        )
        response = client.call_action(
            'create_identity',
            identity=self.request.identity,
        )

        containers.copy_model_to_container(user, self.response.user)
        identity = self.response.identities.add()
        identity.CopyFrom(response.result.identity)


class ValidUser(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        self.response.exists = models.User.objects.filter(
            pk=self.request.user_id,
        ).exists()


class AuthenticateUser(actions.Action):

    def _attach_identities(self):
        client = service.control.Client('identity', token=self.response.token)
        _, response = client.call_action(
            'get_identities',
            user_id=self.response.user.id,
        )
        self.response.user.identities.MergeFrom(response.identities)

    def _handle_authentication(self):
        auth_params = {}
        if self.request.backend == self.request.INTERNAL:
            auth_params['username'] = self.request.credentials.key
            auth_params['password'] = self.request.credentials.secret

        user = authenticate(**auth_params)
        if user is not None:
            if not user.is_active:
                self.note_error(
                    'DISABLED_USER',
                    ('DISABLED_USER', 'user has been disabled'),
                )
        else:
            self.note_error(
                'INVALID_LOGIN',
                ('INVALID_LOGIN', 'user or credentials were invalid'),
            )
        return user

    def run(self, *args, **kwargs):
        user = self._handle_authentication()
        if not self.is_error():
            self.response.authenticated = True
            token, _ = Token.objects.get_or_create(user=user)
            self.response.token = token.key
            containers.copy_model_to_container(user, self.response.user)
            self._attach_identities()
