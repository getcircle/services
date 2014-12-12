from django.db import IntegrityError
import service

from . import models


def _get_credentials(user_id):
    return models.Credential.objects.get_or_none(
        user_id=user_id,
    )


class NewPasswordType(service.StringType):

    def __init__(self, *args, **kwargs):
        super(NewPasswordType, self).__init__(*args, **kwargs)
        self.min_length = 6
        self.max_length = 24


class CreateCredentials(service.Action):

    user_id = service.UUIDType(required=True)
    password = NewPasswordType(required=True)

    success = service.BooleanType(default=False)

    def _create_credentials(self):
        success = True
        credential = models.Credential(
            user_id=self.user_id,
        )
        credential.set_password(self.password)
        try:
            credential.save()
        except IntegrityError:
            success = False
        return success

    def run(self, *args, **kwargs):
        self.success = self._create_credentials()

    class Options:
        roles = {service.public: service.blacklist('password')}


class VerifyCredentials(service.Action):

    user_id = service.UUIDType(required=True)
    password = service.StringType(required=True)

    valid = service.BooleanType(default=False)

    def _verify_credentials(self):
        valid = False
        credential = _get_credentials(self.user_id)
        if credential:
            valid = credential.check_password(self.password)
        return valid

    def run(self, *args, **kwargs):
        self.valid = self._verify_credentials()

    class Options:
        roles = {service.public: service.blacklist('password')}


class UpdateCredentials(service.Action):

    user_id = service.UUIDType(required=True)
    current_password = service.StringType(required=True)
    new_password = NewPasswordType(required=True)

    success = service.BooleanType(default=False)

    def _update_credentials(self):
        success = False
        credential = _get_credentials(self.user_id)
        if credential:
            allowed = credential.check_password(self.current_password)
            if allowed:
                credential.set_password(self.new_password)
                success = True
        return success

    def run(self, *args, **kwargs):
        self.success = self._update_credentials()

    class Options:
        roles = {service.public: service.whitelist('user_id', 'success')}
