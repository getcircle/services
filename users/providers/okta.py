import json
import logging

from django.conf import settings
from itsdangerous import (
    BadSignature,
    Signer,
    URLSafeSerializer,
)
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.organization.containers import sso_pb2
from saml2 import entity
import service.control

from . import base
from .. import models
from ..authentication import utils

logger = logging.getLogger(__name__)


class OktaSSONotEnabled(Exception):
    pass


class ProviderResponseVerificationFailed(Exception):
    pass


class InvalidAuthState(Exception):
    pass


class ProfileNotFound(Exception):
    pass


class ProviderResponseMissingRequiredField(Exception):

    def __init__(self, field, *args, **kwargs):
        message = 'Provider Response missing required field: "%s"' % (field,)
        super(ProviderResponseMissingRequiredField, self).__init__(message)


def get_sso_for_domain(domain):
    try:
        sso = service.control.get_object(
            service='organization',
            action='get_sso',
            return_object='sso',
            organization_domain=domain,
        )
        if not sso.provider == sso_pb2.OKTA:
            raise OktaSSONotEnabled
    except service.control.CallActionError:
        raise OktaSSONotEnabled
    return sso


def get_state_for_user(user, domain):
    totp = models.TOTPToken.objects.totp_for_user(user)
    payload = {
        'totp': totp,
        'user_id': user.id,
        'domain': domain,
    }
    serializer = URLSafeSerializer(settings.SECRET_KEY)
    return serializer.dumps(payload)


def parse_state(state):
    serializer = URLSafeSerializer(settings.SECRET_KEY)
    return serializer.loads(state)


def get_signer(domain):
    return Signer(settings.SECRET_KEY, salt=domain)


class Provider(base.BaseProvider):

    type = user_containers.IdentityV1.OKTA
    exception_to_error_map = {
        BadSignature: 'PROVIDER_RESPONSE_VERIFICATION_FAILED',
        InvalidAuthState: 'INVALID_AUTH_STATE',
        ProviderResponseMissingRequiredField: 'PROVIDER_RESPONSE_MISSING_REQUIRED_FIELD',
        ProviderResponseVerificationFailed: 'PROVIDER_RESPONSE_VERIFICATION_FAILED',
        ProfileNotFound: 'PROFILE_NOT_FOUND',
    }

    def _get_value_for_identity_field(self, field, identity_data, required=True):
        try:
            return identity_data[field][0]
        except (KeyError, IndexError):
            if required:
                raise ProviderResponseMissingRequiredField(field)

    def _profile_exists(self, domain, authentication_identifier):
        response = service.control.call_action(
            service='profile',
            action='profile_exists',
            domain=domain,
            authentication_identifier=authentication_identifier,
        )
        return response.result

    def _complete_authorization_auth_state(self, request, response):
        parsed_state = parse_state(request.saml_details.auth_state)
        user_id = parsed_state['user_id']
        valid = models.TOTPToken.objects.verify_totp_for_user_id(parsed_state['totp'], user_id)
        if not valid:
            raise InvalidAuthState
        return models.Identity.objects.get(provider=self.type, user_id=user_id)

    def complete_authorization(self, request, response, **kwargs):
        domain = request.saml_details.domain
        sso = get_sso_for_domain(domain)
        saml_client = utils.get_saml_client(domain, sso.saml.metadata)
        authn_response = saml_client.parse_authn_request_response(
            request.saml_details.saml_response,
            entity.BINDING_HTTP_POST,
        )
        if authn_response is None:
            logger.warn('failed to complete saml authorization')
            raise ProviderResponseVerificationFailed

        if request.saml_details.relay_state:
            signer = get_signer(request.saml_details.domain)
            redirect_uri = signer.unsign(request.saml_details.relay_state)
            if redirect_uri and utils.valid_redirect_uri(redirect_uri):
                response.redirect_uri = redirect_uri

        user_info = authn_response.get_identity()
        email = self._get_value_for_identity_field('Email', user_info)
        first_name = self._get_value_for_identity_field('FirstName', user_info)
        last_name = self._get_value_for_identity_field('LastName', user_info)
        employee_id = self._get_value_for_identity_field('EmployeeID', user_info, required=False)
        user_info['_provider'] = self.type

        # Authentication Identifier is a unique identifier for the employee
        # within the organization. We prefer EmployeeID, but will fallback to
        # Email if it is not provided
        authentication_identifier = employee_id or email
        profile_exists = self._profile_exists(domain, authentication_identifier)
        if not profile_exists.exists:
            logger.warn(
                'profile not found for: %s in domain: %s (%s)',
                email,
                domain,
                user_info,
            )
            raise ProfileNotFound(json.dumps(user_info))

        identity, created = self.get_identity(authentication_identifier, sso.organization_id)
        identity.email = email
        full_name = ' '.join([first_name, last_name]).strip()
        if full_name:
            identity.full_name = full_name
        identity.data = json.dumps(user_info)
        identity.user_id = profile_exists.user_id
        return identity

    def finalize_authorization(self, identity, user, request, response):
        # generate an auth_state the user can use to authenticate with the SAML backend once
        response.saml_credentials.state = get_state_for_user(user, request.saml_details.domain)

    @classmethod
    def get_authorization_url(self, organization, sso=None, redirect_uri=None, **kwargs):
        if not sso:
            sso = get_sso_for_domain(organization.domain)

        saml_client = utils.get_saml_client(organization.domain, sso.saml.metadata)
        if redirect_uri:
            signer = get_signer(organization.domain)
            redirect_uri = signer.sign(redirect_uri)
        else:
            redirect_uri = None

        _, info = saml_client.prepare_for_authenticate(relay_state=redirect_uri)
        authorization_url = None
        # info['headers'] is an array of key, value tuples
        for key, value in info['headers']:
            if key == 'Location':
                authorization_url = value
        return authorization_url

    def revoke(self, identity):
        pass
