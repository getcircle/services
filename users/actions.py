import json

import boto3
from django.conf import settings
from django.contrib.auth import authenticate
from django.core import validators as django_validators
import django.db
from django.utils import timezone
from protobufs.services.organization.containers import sso_pb2
from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user import containers_pb2 as user_containers
from service import (
    actions,
    validators,
)
import service.control

from services import mixins
from services.token import (
    make_admin_token,
    parse_token,
)
from services.utils import (
    build_slack_message,
    has_field_error,
)

from . import (
    models,
    providers,
)
from .authentication.utils import (
    get_token,
    valid_redirect_uri,
)


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


def create_user(primary_email, organization_id, password=None):
    return models.User.objects.create_user(
        primary_email=primary_email,
        password=password,
        organization_id=organization_id,
    )


class CreateUser(actions.Action):

    required_fields = ('email', 'organization_id')

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
                user = create_user(
                    primary_email=self.request.email,
                    password=self.request.password,
                    organization_id=self.request.organization_id,
                )
            user.to_protobuf(self.response.user)
        except django.db.IntegrityError:
            self.note_field_error('email', 'ALREADY_EXISTS')


class BulkCreateUsers(actions.Action):

    required_fields = ('users', 'organization_id')

    def bulk_create_users(self, protobufs):
        objects = [models.User.objects.from_protobuf(
            user,
            commit=False,
            organization_id=self.request.organization_id,
        ) for user in protobufs]
        return models.User.objects.bulk_create(objects)

    def run(self, *args, **kwargs):
        existing_users = models.User.objects.filter(
            primary_email__in=[x.primary_email for x in self.request.users],
            organization_id=self.request.organization_id,
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


class BulkUpdateUsers(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = ('users',)

    def run(self, *args, **kwargs):
        containers_dict = dict((u.id, u) for u in self.request.users)
        users = models.User.objects.filter(
            organization_id=self.parsed_token.organization_id,
            id__in=[u.id for u in self.request.users],
        )
        for user in users:
            container = containers_dict.get(str(user.id))
            if not container:
                continue

            user.update_from_protobuf(container, organization_id=self.parsed_token.organization_id)

        if users:
            models.User.bulk_manager.bulk_update(users)


class GetUser(mixins.PreRunParseTokenMixin, actions.Action):

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
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


class AuthenticateUser(actions.Action):

    required_fields = ('organization_domain',)

    def _is_internal_backend(self):
        return self.request.backend == self.request.INTERNAL

    def _is_google_backend(self):
        return self.request.backend == self.request.GOOGLE

    def _is_okta_backend(self):
        return self.request.backend == self.request.OKTA

    def _get_auth_params(self, organization):
        auth_params = {
            'organization': organization,
            'backend': self.request.backend,
        }
        if self._is_internal_backend():
            auth_params['username'] = self.request.credentials.key
            auth_params['password'] = self.request.credentials.secret
        elif self._is_google_backend():
            auth_params['code'] = self.request.credentials.key
            auth_params['id_token'] = self.request.credentials.secret
        elif self._is_okta_backend():
            auth_params['state'] = self.request.credentials.secret
        else:
            raise self.ActionFieldError('backend', 'INVALID')
        return auth_params

    def _handle_authentication(self, organization):
        auth_params = self._get_auth_params(organization)
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

    def _get_organization(self, domain):
        try:
            organization = service.control.get_object(
                service='organization',
                action='get_organization',
                return_object='organization',
                domain=domain,
            )
        except service.control.CallActionError as e:
            if has_field_error(e.response, 'domain', 'DOES_NOT_EXIST'):
                raise self.ActionFieldError('organization_domain', 'DOES_NOT_EXIST')
        return organization

    def run(self, *args, **kwargs):
        organization = self._get_organization(self.request.organization_domain)
        user = self._handle_authentication(organization)
        user.last_login = timezone.now()
        user.save()
        self.response.token = get_token(user, self.request.client_type)
        self.service_control.token = self.response.token
        self.response.new_user = user.new
        user.to_protobuf(self.response.user)


class Logout(actions.Action):

    def _delete_token_for_client(self, service_token, client_type):
        try:
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
        self.service_control.token = ''


def get_authorization_instructions(
        provider,
        organization=None,
        sso=None,
        redirect_uri=None,
        login_hint=None,
    ):
    """Return authorization instructions for the given provider.

    Args:
        provider (protobufs.services.user.containers_pb2.IdentityV1): identity
            provider we're requesting authorization instructions for.
        organization (Optional[organization.containers.OrganizationV1]): the
            organization container if applicable. If the identity is being used
            for authentication, this is required.
        sso (Optional[organization.containers.SSOV1]): the organization's SSO
            container if applicable.
        redirect_uri (Optional[str]): redirect_uri we want the identity
            provider to redirect to.
        login_hint (Optional[str]): the login_hint we want the identity
            provider to use

    Returns:
        tuple: tuple of authorization_url (str), provider_name (str)

    Raises:
        providers.okta.OktaSSONotEnabled: If
            `user.containers.IdentityV1.OKTA` is specified but the organization
            doesn't have Okta configured for SSO.
        providers.google.GoogleSSONotEnabled: If
            `user.containers.IdentityV1.GOOGLE` is specified but the
            organization doesn't have Google configured for SSO.

    """
    authorization_url = None
    provider_name = None
    if provider == user_containers.IdentityV1.GOOGLE:
        authorization_url = providers.google.Provider.get_authorization_url(
            organization=organization,
            sso=sso,
            login_hint=login_hint,
            redirect_uri=redirect_uri,
        )
        provider_name = 'Google'
    elif provider == user_containers.IdentityV1.OKTA:
        authorization_url = providers.okta.Provider.get_authorization_url(
            organization=organization,
            sso=sso,
            redirect_uri=redirect_uri,
        )
        provider_name = 'Okta'
    elif provider == user_containers.IdentityV1.SLACK:
        authorization_url = providers.slack.Provider.get_authorization_url(
            organization=organization,
            redirect_uri=redirect_uri,
        )
        provider_name = 'Slack'
    return authorization_url, provider_name


class CompleteAuthorization(actions.Action):

    def _get_provider(self):
        provider_class = None
        if self.request.provider == user_containers.IdentityV1.GOOGLE:
            provider_class = providers.Google
        elif self.request.provider == user_containers.IdentityV1.OKTA:
            provider_class = providers.Okta
        elif self.request.provider == user_containers.IdentityV1.SLACK:
            provider_class = providers.Slack

        if provider_class is None:
            raise self.ActionFieldError('provider', 'UNSUPPORTED')

        self.exception_to_error_map.update(provider_class.exception_to_error_map)
        return provider_class()

    def _get_state(self):
        state = {}
        if self.request.oauth2_details.ByteSize():
            state = providers.parse_state_token(
                self.request.provider,
                self.request.oauth2_details.state,
            )
        return state

    def _get_or_create_user(self, identity):
        user_id = identity.user_id
        organization_id = identity.organization_id
        if not user_id:
            try:
                user = create_user(
                    primary_email=identity.email,
                    organization_id=organization_id,
                )
                self.response.new_user = True
            except django.db.IntegrityError:
                user = models.User.objects.get(
                    organization_id=organization_id,
                    primary_email=identity.email,
                )
            user.to_protobuf(self.response.user)
        else:
            user = models.User.objects.get(
                pk=user_id,
                organization_id=organization_id,
            ).to_protobuf(self.response.user)
        return self.response.user

    def run(self, *args, **kwargs):
        provider = self._get_provider()
        state = self._get_state()
        identity = provider.complete_authorization(
            self.request,
            self.response,
            state=state,
        )
        user = None
        if not isinstance(provider, providers.Slack):
            user = self._get_or_create_user(identity)
            identity.user_id = user.id
            identity.organization_id = user.organization_id
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
                    provider = providers.Google()
                    provider.revoke(identity, self.token)
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

    required_fields = ('anonymous_user',)

    def _get_provider_name(self, provider):
        provider_dict = dict(zip(
            user_containers.IdentityV1.ProviderV1.values(),
            user_containers.IdentityV1.ProviderV1.keys(),
        ))
        return provider_dict.get(provider, 'Unknown (%s)' % (provider,))

    def _get_admin_emails(self, domain):
        organization = service.control.get_object(
            service='organization',
            action='get_organization',
            return_object='organization',
            client_kwargs={'token': make_admin_token()},
            domain=domain,
        )
        profiles = service.control.get_object(
            service='profile',
            action='get_profiles',
            return_object='profiles',
            client_kwargs={'token': make_admin_token(organization_id=organization.id)},
            inflations={'disabled': True},
            fields={'only': ['email']},
            is_admin=True,
        )
        return [p.email for p in profiles]

    def _get_email_message(self, user, admin_emails, user_info, provider_name):
        return '%s\n%s\n\nAdmins:\n%s\n\n%s Response:\n%s' % (
            user.domain,
            user.location,
            ', '.join(admin_emails),
            provider_name,
            json.dumps(user_info),
        )

    def _get_lambda_message(self, user, admin_emails, user_info, provider_name):
        attachments = [
            {
                'fallback': '[%s] Access Request' % (user.domain,),
                'pretext': '[%s] Access Request' % (user.domain,),
                'fields': [
                    {
                        'title': 'Domain',
                        'value': user.domain,
                        'short': True,
                    },
                    {
                        'title': 'Location',
                        'value': user.location,
                        'short': True,
                    },
                    {
                        'title': 'Admins',
                        'value': ', '.join(admin_emails),
                        'short': False,
                    },
                ],
            },
            {
                'pretext': '%s Response' % (provider_name,),
                'fields': [{'title': key, 'value': value[0], 'short': True}
                           for key, value in user_info.iteritems()],
            },
        ]
        return build_slack_message(attachments, '#access-requests')

    def _anonymous_user_request(self):
        user = self.request.anonymous_user
        user_info = {}
        if user.user_info:
            user_info = json.loads(user.user_info)

        provider_name = self._get_provider_name(user_info.pop('_provider', None))
        sns = boto3.resource('sns', **settings.AWS_SNS_KWARGS)
        topic = sns.Topic(settings.AWS_SNS_TOPIC_REQUEST_ACCESS)
        admin_emails = self._get_admin_emails(user.domain)
        topic.publish(
            Subject='[%s] Access Request' % (user.domain,),
            Message=json.dumps({
                'default': self._get_email_message(user, admin_emails, user_info, provider_name),
                'lambda': self._get_lambda_message(user, admin_emails, user_info, provider_name),
            }),
            MessageStructure='json',
        )

    def run(self, *args, **kwargs):
        self._anonymous_user_request()


class GetAuthenticationInstructions(actions.Action):

    required_fields = ('organization_domain',)

    type_validators = {
        'email': [validate_email],
        'redirect_uri': [valid_redirect_uri],
    }

    def _get_authorization_instructions(self, provider, organization, sso, **kwargs):
        return get_authorization_instructions(
            provider=provider,
            login_hint=self.request.email,
            organization=organization,
            redirect_uri=self.request.redirect_uri,
            sso=sso,
        )

    def _populate_instructions(self, provider, organization, sso):
        instructions = self._get_authorization_instructions(provider, organization, sso)
        self.response.authorization_url, self.response.provider_name = instructions

    def _populate_google_instructions(self, organization, sso):
        self.response.backend = authenticate_user_pb2.RequestV1.GOOGLE
        self._populate_instructions(user_containers.IdentityV1.GOOGLE, organization, sso)

    def _populate_okta_instructions(self, organization, sso):
        self.response.backend = authenticate_user_pb2.RequestV1.OKTA
        self._populate_instructions(user_containers.IdentityV1.OKTA, organization, sso)

    def _get_organization_sso(self, domain):
        try:
            response = service.control.call_action(
                service='organization',
                action='get_sso',
                organization_domain=domain,
            )
        except service.control.CallActionError:
            return None

        if not bool(response.result.sso.ByteSize()):
            return None

        return response.result.sso

    def _should_force_internal_authentication(self, email):
        return email in settings.USER_SERVICE_FORCE_INTERNAL_AUTH

    def _should_force_organization_internal_auth(self, domain):
        return domain in settings.USER_SERVICE_FORCE_DOMAIN_INTERNAL_AUTH

    def _get_organization(self, domain):
        try:
            response = service.control.call_action(
                'organization',
                'get_organization',
                domain=domain,
            )
        except service.control.CallActionError as e:
            error_details = e.response.error_details
            if error_details:
                details = error_details[0]
                if details.key == 'domain' and details.detail == 'DOES_NOT_EXIST':
                    raise self.ActionFieldError('organization_domain', 'DOES_NOT_EXIST')
            raise
        return response.result.organization

    def run(self, *args, **kwargs):
        organization = self._get_organization(self.request.organization_domain)

        if organization.image_url:
            self.response.organization_image_url = organization.image_url

        sso = self._get_organization_sso(organization.domain)
        if self._should_force_internal_authentication(self.request.email):
            self.response.backend = authenticate_user_pb2.RequestV1.INTERNAL
        elif self._should_force_organization_internal_auth(organization.domain):
            self.response.backend = authenticate_user_pb2.RequestV1.INTERNAL
        elif sso and sso.provider == sso_pb2.OKTA:
            self._populate_okta_instructions(organization, sso)
        elif sso and sso.provider == sso_pb2.GOOGLE:
            self._populate_google_instructions(organization, sso)
        else:
            self.response.backend = authenticate_user_pb2.RequestV1.INTERNAL


class GetIntegrationAuthenticationInstructions(actions.Action):

    required_fields = ('organization_domain', 'redirect_uri', 'provider',)

    type_validators = {
        'redirect_uri': [valid_redirect_uri],
    }

    def _get_authorization_instructions(self, organization, provider):
        return get_authorization_instructions(
            provider=provider,
            organization=organization,
            redirect_uri=self.request.redirect_uri,
        )

    def _populate_instructions(self, organization, provider):
        self.response.authorization_url, _ = self._get_authorization_instructions(organization, provider)

    def _get_organization(self, domain):
        try:
            response = service.control.call_action(
                'organization',
                'get_organization',
                domain=domain,
            )
        except service.control.CallActionError as e:
            error_details = e.response.error_details
            if error_details:
                details = error_details[0]
                if details.key == 'domain' and details.detail == 'DOES_NOT_EXIST':
                    raise self.ActionFieldError('organization_domain', 'DOES_NOT_EXIST')
            raise
        return response.result.organization

    def run(self, *args, **kwargs):
        organization = self._get_organization(self.request.organization_domain)
        self._populate_instructions(organization, self.request.provider)


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
