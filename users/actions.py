from django.conf import settings
from django.contrib.auth import authenticate
import django.db
from protobufs.user_service_pb2 import UserService
import pyotp
from rest_framework.authtoken.models import Token
from twilio.rest import TwilioRestClient
from twilio.rest.exceptions import TwilioRestException
from service import (
    actions,
    validators,
)
import service.control

from services.token import (
    make_token,
    parse_token,
)

from . import (
    models,
    providers,
)


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

    required_fields = ('email',)

    def validate(self, *args, **kwargs):
        super(CreateUser, self).validate(*args, **kwargs)
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


class UpdateUser(actions.Action):

    # XXX this isn't working if a protobuf instance is passed
    type_validators = {
        'user.id': [validators.is_uuid4],
    }

    field_validators = {
        'user.id': {
            valid_user: 'DOES_NOT_EXIST',
        }
    }

    def run(self, *args, **kwargs):
        user = models.User.objects.get(pk=self.request.user.id)
        user.update_from_protobuf(self.request.user)
        user.save()
        user.to_protobuf(self.response.user)


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
                raise self.ActionError(
                    'DISABLED_USER',
                    ('DISABLED_USER', 'user has been disabled'),
                )
        else:
            raise self.ActionError(
                'INVALID_LOGIN',
                ('INVALID_LOGIN', 'user or credentials were invalid'),
            )
        return user

    def _get_profile(self, user_id, token):
        profile = None
        client = service.control.Client('profile', token=token)
        try:
            response = client.call_action('get_profile', user_id=str(user_id))
            profile = response.result.profile
        except service.control.Client.CallActionError:
            profile = None
        return profile

    def _get_token(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        # XXX this assumes that we have profiles already set up
        temporary_token = make_token(auth_token=token.key, user_id=user.id)
        profile = self._get_profile(user.id, temporary_token)
        return make_token(
            auth_token=token.key,
            profile_id=getattr(profile, 'id', None),
            user_id=user.id,
            organization_id=getattr(profile, 'organization_id', None),
        )

    def run(self, *args, **kwargs):
        user = self._handle_authentication()
        self.response.authenticated = True
        self.response.token = self._get_token(user)
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
            user = models.User.objects.get(pk=self.request.user_id)
            user.phone_number_verified = True
            user.save()
            self.response.verified = True


class GetAuthorizationInstructions(actions.Action):

    def run(self, *args, **kwargs):
        if self.request.provider == UserService.LINKEDIN:
            self.response.authorization_url = providers.Linkedin.get_authorization_url(
                token=self.token,
            )


class CompleteAuthorization(actions.Action):

    def __init__(self, *args, **kwargs):
        super(CompleteAuthorization, self).__init__(*args, **kwargs)
        self.exception_to_error_map.update(providers.Linkedin.exception_to_error_map)

    def validate(self, *args, **kwargs):
        super(CompleteAuthorization, self).validate(*args, **kwargs)
        self.payload = providers.parse_state_token(
            self.request.provider,
            self.request.oauth2_details.state,
        )
        if self.payload is None:
            raise self.ActionFieldError('oauth2_details.state', 'INVALID')

    def run(self, *args, **kwargs):
        provider = None
        if self.request.provider == UserService.LINKEDIN:
            provider = providers.Linkedin()

        if provider is None:
            raise self.ActionFieldError('provider', 'UNSUPPORTED')

        token = self.token or self.payload.get('token')
        identity = provider.complete_authorization(self.request.oauth2_details)
        if not token:
            # XXX add some concept of "generate_one_time_use_admin_token"
            client = service.control.Client('user', token='one-time-use-token')
            response = client.call_action('create_user', email=identity.email)
            user = response.result.user
            identity.user_id = user.id
            self.response.user.CopyFrom(user)
        else:
            token = parse_token(token)
            user = models.User.objects.get(pk=token.user_id).to_protobuf(self.response.user)
            identity.user_id = token.user_id

        identity.save()
        identity.to_protobuf(self.response.identity)
