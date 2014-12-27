from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from service import (
    actions,
    validators,
)

from . import models


def validate_new_password_min_length(value):
    return False if len(value) < 6 else True


def validate_new_password_max_length(value):
    return False if len(value) > 24 else True


class CreateUser(actions.Action):

    def validate(self, *args, **kwargs):
        super(CreateUser, self).validate(*args, **kwargs)
        # XXX if we had some concept of required this wouldn't be necessary
        if not self.is_error() and self.request.password:
            if not validate_new_password_min_length(self.request.password):
                self.note_field_error('password', 'INVALID_MIN_LENGTH')
            elif not validate_new_password_max_length(self.request.password):
                self.note_field_error('password', 'INVALID_MAX_LENGTH')

    def run(self, *args, **kwargs):
        user = models.User.objects.create_user(
            primary_email=self.request.email,
            password=self.request.password,
        )
        user.to_protobuf(self.response.user)


class ValidUser(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        self.response.exists = models.User.objects.filter(
            pk=self.request.user_id,
        ).exists()


class AuthenticateUser(actions.Action):

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
            user.to_protobuf(self.response.user)
