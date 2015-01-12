from django.conf import settings
from django.contrib.auth import authenticate
import django.db
import pyotp
from rest_framework.authtoken.models import Token
from twilio.rest import TwilioRestClient
from twilio.rest.exceptions import TwilioRestException
from service import (
    actions,
    validators,
)

from . import models


def validate_new_password_min_length(value):
    return False if len(value) < 6 else True


def validate_new_password_max_length(value):
    return False if len(value) > 24 else True


def valid_user(value):
    return models.User.objects.filter(pk=value).exists()


def get_totp_code(token):
    totp = pyotp.TOTP(token, interval=settings.USER_SERVICE_TOTP_INTERVAL)
    return str(totp.now())


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
        try:
            user = models.User.objects.create_user(
                primary_email=self.request.email,
                password=self.request.password,
            )
            user.to_protobuf(self.response.user)
        except django.db.IntegrityError:
            self.note_field_error('email', 'ALREADY_EXISTS')


class GetUser(actions.Action):

    def run(self, *args, **kwargs):
        user = models.User.objects.get_or_none(primary_email=self.request.email)
        if user is None:
            self.note_field_error('email', 'DOES_NOT_EXIST')
        else:
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


class SendVerificationCode(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    field_validators = {
        'user_id': {
            valid_user: 'DOES_NOT_EXIST',
        }
    }

    def __init__(self, *args, **kwargs):
        super(SendVerificationCode, self).__init__(*args, **kwargs)
        self.twilio_client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )

    def validate(self, *args, **kwargs):
        super(SendVerificationCode, self).validate(*args, **kwargs)
        if not self.is_error():
            self.user = models.User.objects.get(pk=self.request.user_id)
            if not self.user.phone_number:
                # XXX we should be raising actual exceptions here and mapping them
                self.note_error(
                    'NO_PHONE_NUMBER',
                    ('NO_PHONE_NUMBER', 'user must have a phone number set'),
                )

    def run(self, *args, **kwargs):
        # clear out any previously created tokens
        models.TOTPToken.objects.filter(user=self.user).delete()
        # TODO it would be more fitting to put these in redis
        token = models.TOTPToken.objects.create(user=self.user)
        # TODO we should be logging the response of this message
        try:
            message = self.twilio_client.messages.create(
                body='Your verification code: %s' % (get_totp_code(token.token),),
                to=self.user.phone_number.as_international,
                from_=settings.TWILIO_PHONE_NUMBER,
            )
        except TwilioRestException as e:
            self.note_error('FAILED', ('FAILED', e.msg))
        else:
            self.response.message_id = message.sid


class VerifyVerificationCode(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    field_validators = {
        'user_id': {
            valid_user: 'DOES_NOT_EXIST',
        }
    }

    def run(self, *args, **kwargs):
        token = models.TOTPToken.objects.get(user_id=self.request.user_id)
        if get_totp_code(token.token) != self.request.code:
            self.note_field_error('code', 'INVALID')
        else:
            self.response.verified = True
