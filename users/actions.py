from cacheops import cached
from django.conf import settings
from django.contrib.auth import authenticate
from django.core import validators as django_validators
import django.db
import DNS
from phonenumber_field.validators import validate_international_phonenumber
from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user import containers_pb2 as user_containers
from twilio.rest import TwilioRestClient
from twilio.rest.exceptions import TwilioRestException
from service import (
    actions,
    validators,
)
import service.control

from services import mixins
from services.token import parse_token

from . import (
    models,
    providers,
)
from .authentication.utils import get_token


def validate_new_password_min_length(value):
    return False if len(value) < 6 else True


def validate_new_password_max_length(value):
    return False if len(value) > 24 else True


def valid_user(value):
    return models.User.objects.filter(pk=value).exists()


def validate_email(value):
    valid = False
    try:
        django_validators.validate_email(value)
        valid = True
    except django_validators.ValidationError:
        pass
    return valid


def validate_phone_number(value):
    valid = False
    try:
        validate_international_phonenumber(value)
        valid = True
    except django_validators.ValidationError:
        pass
    return valid


def unique_phone_number(value):
    return not models.User.objects.filter(phone_number=value).exists()


@cached(timeout=settings.CACHEOPS_FUNC_IS_GOOGLE_DOMAIN_TIMEOUT)
def is_google_domain(domain):
    mail_exchangers = DNS.mxlookup(domain)

    def is_google_mx(mx):
        mx = mx.strip().lower()
        return mx.endswith('google.com') or mx.endswith('googlemail.com')
    return any([is_google_mx(mx) for _, mx in mail_exchangers])


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
            with django.db.transaction.atomic():
                user = models.User.objects.create_user(
                    primary_email=self.request.email,
                    password=self.request.password,
                )
            user.to_protobuf(self.response.user)
        except django.db.IntegrityError:
            self.note_field_error('email', 'ALREADY_EXISTS')


class BulkCreateUsers(actions.Action):

    @classmethod
    def bulk_create_users(cls, protobufs):
        objects = [models.User.objects.from_protobuf(user, commit=False) for user in protobufs]
        return models.User.objects.bulk_create(objects)

    def run(self, *args, **kwargs):
        existing_users = models.User.objects.filter(
            primary_email__in=[x.primary_email for x in self.request.users],
        )
        existing_users_dict = dict((user.primary_email, user) for user in existing_users)
        users_to_create = []
        for user in self.request.users:
            if user.primary_email not in existing_users_dict:
                users_to_create.append(user)

        users = self.bulk_create_users(users_to_create)
        for user in list(users) + list(existing_users):
            container = self.response.users.add()
            user.to_protobuf(container)


class UpdateUser(actions.Action):

    # XXX this isn't working if a protobuf instance is passed
    type_validators = {
        'user.id': [validators.is_uuid4],
    }

    field_validators = {
        'user.id': {
            valid_user: 'DOES_NOT_EXIST',
        },
        'user.phone_number': {
            unique_phone_number: 'DUPLICATE',
            validate_phone_number: 'INVALID',
        },
    }

    def run(self, *args, **kwargs):
        user = models.User.objects.get(pk=self.request.user.id)
        user.update_from_protobuf(self.request.user)
        user.save()
        user.to_protobuf(self.response.user)


class GetUser(actions.Action):

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.email:
            parameters['primary_email'] = self.request.email
        else:
            token = parse_token(self.token)
            parameters['pk'] = token.user_id

        user = models.User.objects.get_or_none(**parameters)
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

    required_fields = ('client_type',)

    def _is_internal_backend(self):
        return self.request.backend == self.request.INTERNAL

    def _is_google_backend(self):
        return self.request.backend == self.request.GOOGLE

    def _is_saml_backend(self):
        return self.request.backend == self.request.SAML

    def _get_auth_params(self):
        auth_params = {}
        if self._is_internal_backend():
            auth_params['username'] = self.request.credentials.key
            auth_params['password'] = self.request.credentials.secret
        elif self._is_google_backend():
            auth_params['code'] = self.request.credentials.key
            auth_params['id_token'] = self.request.credentials.secret
            auth_params['client_type'] = self.request.client_type
        elif self._is_saml_backend():
            auth_params['auth_state'] = self.request.credentials.secret
        else:
            raise self.ActionFieldError('backend', 'INVALID')
        return auth_params

    def _handle_authentication(self):
        auth_params = self._get_auth_params()
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
            response = client.call_action('get_profile')
            profile = response.result.profile
        except service.control.CallActionError:
            profile = None
        return profile

    def run(self, *args, **kwargs):
        user = self._handle_authentication()
        self.response.token = get_token(user, self.request.client_type)
        self.response.new_user = user.new
        user.to_protobuf(self.response.user)


class Logout(actions.Action):

    def validate(self, *args, **kwargs):
        super(Logout, self).validate(*args, **kwargs)
        if (
            not self.is_error() and
            not self.request.HasField('client_type') and
            not self.request.HasField('revoke_all')
        ):
            raise self.ActionFieldError('client_type', 'MISSING')

    def _delete_token_for_client(self, service_token, client_type):
        try:
            # TODO see if we really need client_type
            models.Token.objects.get(
                key=service_token.auth_token,
                user_id=service_token.user_id,
                client_type=self.request.client_type,
            ).delete()
        except models.Token.DoesNotExist:
            pass

    def _delete_all_tokens_for_user(self, service_token):
        models.Token.objects.filter(user_id=service_token.user_id).delete()

    def run(self, *args, **kwargs):
        token = parse_token(self.token)
        if self.request.revoke_all:
            self._delete_all_tokens_for_user(token)
        else:
            self._delete_token_for_client(token, self.request.client_type)


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
        totp = models.TOTPToken.objects.totp_for_user(self.user)
        # TODO we should be logging the response of this message
        try:
            message = self.twilio_client.messages.create(
                body='Your verification code: %s' % (totp,),
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
        valid = models.TOTPToken.objects.verify_totp_for_user_id(
            self.request.code,
            self.request.user_id,
        )
        if not valid:
            self.note_field_error('code', 'INVALID')
        else:
            user = models.User.objects.get(pk=self.request.user_id)
            user.phone_number_verified = True
            user.save()
            self.response.verified = True


class GetAuthorizationInstructions(actions.Action):

    def run(self, *args, **kwargs):
        if self.request.provider == user_containers.IdentityV1.GOOGLE:
            self.response.authorization_url = providers.google.Provider.get_authorization_url(
                token=self.token,
                login_hint=self.request.login_hint,
                redirect_uri=self.request.redirect_uri,
            )
        elif self.request.provider == user_containers.IdentityV1.SAML:
            try:
                self.response.authorization_url = providers.saml.Provider.get_authorization_url(
                    domain=self.request.domain,
                    redirect_uri=self.request.redirect_uri,
                )
            except providers.saml.SAMLMetaDataDoesNotExist:
                raise self.ActionFieldError('domain', 'DOES_NOT_EXIST')


class CompleteAuthorization(actions.Action):

    def _get_provider_class(self):
        provider_class = None
        if self.request.provider == user_containers.IdentityV1.GOOGLE:
            provider_class = providers.Google
        elif self.request.provider == user_containers.IdentityV1.SAML:
            provider_class = providers.SAML

        if provider_class is None:
            self.ActionFieldError('provider', 'UNSUPPORTED')

        self.exception_to_error_map.update(provider_class.exception_to_error_map)
        return provider_class

    def validate(self, *args, **kwargs):
        super(CompleteAuthorization, self).validate(*args, **kwargs)
        self.provider_class = self._get_provider_class()
        self.payload = {}
        if self.request.HasField('oauth2_details'):
            self.payload = providers.parse_state_token(
                self.request.provider,
                self.request.oauth2_details.state,
            )
            if self.payload is None:
                if not self.provider_class.csrf_exempt:
                    raise self.ActionFieldError('oauth2_details.state', 'INVALID')
                else:
                    self.payload = {}

    def _get_or_create_user(self, identity, token):
        user_id = identity.user_id or getattr(token, 'user_id', None)
        if not user_id:
            # XXX add some concept of "generate_one_time_use_admin_token"
            client = service.control.Client('user', token='one-time-use-token')
            try:
                response = client.call_action('create_user', email=identity.email)
                self.response.new_user = True
            except service.control.CallActionError as e:
                if 'FIELD_ERROR' in e.response.errors:
                    field_error = e.response.error_details[0]
                    if field_error.key == 'email' and field_error.detail == 'ALREADY_EXISTS':
                        response = client.call_action('get_user', email=identity.email)
                    else:
                        raise
                else:
                    raise

            user = response.result.user
            self.response.user.CopyFrom(user)
        else:
            user = models.User.objects.get(pk=user_id).to_protobuf(self.response.user)
        return self.response.user

    def run(self, *args, **kwargs):
        token = self.token or self.payload.get('token')
        if token:
            token = parse_token(token)

        provider = self.provider_class(token)
        identity = provider.complete_authorization(
            self.request,
            self.response,
            redirect_uri=self.payload.get('redirect_uri'),
        )
        user = self._get_or_create_user(identity, token)
        identity.user_id = user.id
        identity.save()
        identity.to_protobuf(self.response.identity)
        provider.finalize_authorization(
            identity=identity,
            user=user,
            request=self.request,
            response=self.response,
        )


class DeleteIdentity(actions.Action):

    required_fields = (
        'identity.id',
        'identity.user_id',
    )

    type_validators = {
        'identity.id': [validators.is_uuid4],
        'identity.user_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        identity = models.Identity.objects.get_or_none(
            id=self.request.identity.id,
        )
        if identity:
            if identity.provider == user_containers.IdentityV1.GOOGLE:
                try:
                    provider = providers.Google(token=self.token)
                    provider.revoke(identity)
                except providers.ProviderAPIError as e:
                    raise self.ActionError(
                        'PROVIDER_API_ERROR',
                        ('PROVIDER_API_ERROR', getattr(e.response, 'reason', 'Failure')),
                    )
            identity.delete()


class GetIdentities(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        identities = models.Identity.objects.filter(user_id=self.request.user_id)
        self.paginated_response(
            self.response.identities,
            identities,
            lambda item, container: item.to_protobuf(container.add()),
        )


class RecordDevice(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = (
        # XXX should only accept this from the token
        'device.user_id',
        'device.platform',
        'device.os_version',
        'device.device_uuid',
        'device.app_version',
    )

    type_validators = {
        'device.user_id': [validators.is_uuid4],
    }

    field_validators = {
        'device.user_id': {
            valid_user: 'DOES_NOT_EXIST',
        },
    }

    def _register_device_for_notifications(self, device):
        if device.notification_token:
            client = service.control.Client('notification', token=self.token)
            client.call_action('register_device', device=device)

    # XXX should pull user_id from token
    def run(self, *args, **kwargs):
        try:
            device = models.Device.objects.get(device_uuid=self.request.device.device_uuid)
            device.update_from_protobuf(
                self.request.device,
                last_token_id=self.parsed_token.auth_token_id,
            )
            device.save()
        except models.Device.DoesNotExist:
            device = models.Device.objects.from_protobuf(
                self.request.device,
                last_token_id=self.parsed_token.auth_token_id,
            )

        device.to_protobuf(self.response.device)
        self._register_device_for_notifications(self.response.device)


class RequestAccess(actions.Action):

    required_fields = ('user_id',)

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    field_validators = {
        'user_id': {
            valid_user: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        access_request, _ = models.AccessRequest.objects.get_or_create(
            user_id=self.request.user_id,
        )
        access_request.to_protobuf(self.response.access_request)


class GetAuthenticationInstructions(actions.Action):

    type_validators = {
        'email': [validate_email],
    }

    def validate(self, *args, **kwargs):
        super(GetAuthenticationInstructions, self).validate(*args, **kwargs)
        if (
            self.request.redirect_uri and
            self.request.redirect_uri not in settings.USER_SERVICE_ALLOWED_REDIRECT_URIS
        ):
            self.request.ClearField('redirect_uri')

        if not (self.request.HasField('email') or self.request.HasField('organization_domain')):
            raise self.ActionError(
                'MISSING_REQUIRED_PARAMETERS',
                (
                    'MISSING_REQUIRED_PARAMETERS',
                    'must provide either "email" or "organization_domain"',
                ),
            )

    def _populate_google_instructions(self):
        self.response.backend = authenticate_user_pb2.RequestV1.GOOGLE
        self.response.authorization_url = service.control.get_object(
            service='user',
            action='get_authorization_instructions',
            return_object='authorization_url',
            client_kwargs={'token': self.token},
            provider=user_containers.IdentityV1.GOOGLE,
            login_hint=self.request.email,
            redirect_uri=self.request.redirect_uri,
        )

    def _populate_saml_instructions(self, domain):
        self.response.backend = authenticate_user_pb2.RequestV1.SAML
        self.response.authorization_url = service.control.get_object(
            service='user',
            action='get_authorization_instructions',
            return_object='authorization_url',
            provider=user_containers.IdentityV1.SAML,
            redirect_uri=self.request.redirect_uri,
            domain=domain,
        )

    def _get_organization_sso(self, domain):
        try:
            response = service.control.call_action(
                'organization',
                'get_sso_metadata',
                organization_domain=domain,
            )
        except service.control.CallActionError:
            return None

        if not response.result.HasField('sso'):
            return None

        return response.result.sso

    def _get_domain(self):
        if self.request.HasField('organization_domain'):
            return self.request.organization_domain

        try:
            return self.request.email.split('@', 1)[1].split('.', 1)[0]
        except IndexError:
            return None

    def _is_email_google_domain(self):
        if self.request.HasField('email'):
            domain = self.request.email.split('@', 1)[1]
            return is_google_domain(domain)

    def _should_force_internal_authentication(self):
        return self.request.email in settings.USER_SERVICE_FORCE_INTERNAL_AUTH

    def _should_force_google_authentication(self):
        return self.request.email in settings.USER_SERVICE_FORCE_GOOGLE_AUTH

    def _should_force_organization_internal_auth(self, domain):
        return domain in settings.USER_SERVICE_FORCE_DOMAIN_INTERNAL_AUTH

    def run(self, *args, **kwargs):
        if self.request.HasField('email'):
            self.response.user_exists = models.User.objects.filter(
                primary_email=self.request.email,
            ).exists()

        domain = self._get_domain()
        sso = self._get_organization_sso(domain)
        if self._should_force_internal_authentication():
            self.response.backend = authenticate_user_pb2.RequestV1.INTERNAL
        elif self._should_force_google_authentication() and self._is_email_google_domain():
            self._populate_google_instructions()
        elif self._should_force_organization_internal_auth(domain):
            self.response.backend = authenticate_user_pb2.RequestV1.INTERNAL
        elif sso:
            self._populate_saml_instructions(domain)
        elif self._is_email_google_domain():
            self._populate_google_instructions()
        else:
            self.response.backend = authenticate_user_pb2.RequestV1.INTERNAL


class GetActiveDevices(actions.Action):

    required_fields = ('user_id',)

    def run(self, *args, **kwargs):
        active_auth_tokens = models.Token.objects.filter(
            user_id=self.request.user_id,
        ).values_list('pk', flat=True)
        if active_auth_tokens:
            active_devices = models.Device.objects.filter(
                user_id=self.request.user_id,
                last_token_id__in=active_auth_tokens,
            )
            for device in active_devices:
                container = self.response.devices.add()
                device.to_protobuf(container)
