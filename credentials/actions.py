from django.db import IntegrityError
from service import (
    actions,
    validators,
)

from . import models


def _get_credentials(user_id):
    return models.Credential.objects.get_or_none(
        user_id=user_id,
    )


def validate_new_password_min_length(value):
    return False if len(value) < 6 else True


def validate_new_password_max_length(value):
    return False if len(value) > 24 else True


class CreateCredentials(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    field_validators = {
        'password': {
            validate_new_password_min_length: 'INVALID_MIN_LENGTH',
            validate_new_password_max_length: 'INVALID_MAX_LENGTH',
        }
    }

    # TODO add some concept of required fields on the action

    def _create_credentials(self):
        success = True
        credential = models.Credential(
            user_id=self.request.user_id,
        )
        credential.set_password(self.request.password)
        try:
            credential.save()
        except IntegrityError:
            success = False
        return success

    def run(self, *args, **kwargs):
        import ipdb; ipdb.set_trace()
        if not self._create_credentials():
            self.note_error(
                'DUPLICATE',
                ('DUPLICATE', 'credentials already exist for user'),
            )


class VerifyCredentials(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    def _verify_credentials(self):
        valid = False
        credential = _get_credentials(self.request.user_id)
        if credential:
            valid = credential.check_password(self.request.password)
        return valid

    def run(self, *args, **kwargs):
        self.response.valid = self._verify_credentials()


class UpdateCredentials(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    field_validators = {
        'new_password': {
            validate_new_password_min_length: 'INVALID_MIN_LENGTH',
            validate_new_password_max_length: 'INVALID_MAX_LENGTH',
        }
    }

    def _update_credentials(self):
        success = False
        credential = _get_credentials(self.request.user_id)
        if credential:
            allowed = credential.check_password(self.request.current_password)
            if allowed:
                credential.set_password(self.request.new_password)
                success = True
        return success

    def run(self, *args, **kwargs):
        if not self._update_credentials():
            self.note_error(
                'FAILED',
                ('FAILED', 'current password is invalid'),
            )
