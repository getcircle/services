import json

from django.conf import settings
from itsdangerous import (
    BadSignature,
    Signer,
    URLSafeSerializer,
)
from protobufs.services.user import containers_pb2 as user_containers
from saml2 import entity
import service.control

from . import base
from .. import models
from ..authentication import utils


class SAMLMetaDataDoesNotExist(Exception):
    pass


class ProviderResponseVerificationFailed(Exception):
    pass


class InvalidAuthState(Exception):
    pass


class ProviderResponseMissingRequiredField(Exception):

    def __init__(self, field, *args, **kwargs):
        message = 'Provider Response missing required field: "%s"' % (field,)
        super(ProviderResponseMissingRequiredField, self).__init__(message)


def get_sso_for_domain(domain):
    client = service.control.Client('organization')
    try:
        response = client.call_action('get_sso_metadata', organization_domain=domain)
    except service.control.CallActionError:
        raise SAMLMetaDataDoesNotExist
    return response.result.sso


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
        SAMLMetaDataDoesNotExist: 'SAML_METADATA_DOES_NOT_EXIST',
    }

    def _get_value_for_identity_field(self, field, identity_data):
        try:
            return identity_data[field][0]
        except (KeyError, IndexError):
            raise ProviderResponseMissingRequiredField(field)

    def _verify_profile_exists(self, domain, email):
        organization = service.control.get_object(
            service='organization',
            action='get_organization',
            return_object='organization',
            domain=domain,
        )
        return service.control.get_object(
            service='profile',
            action='profile_exists',
            return_object='exists',
            organization_id=organization.id,
            email=email,
        )

    def _complete_authorization(self, request, response):
        domain = request.saml_details.domain
        sso = get_sso_for_domain(domain)
        saml_client = utils.get_saml_client(domain, sso.metadata)
        authn_response = saml_client.parse_authn_request_response(
            request.saml_details.saml_response,
            entity.BINDING_HTTP_POST,
        )
        if authn_response is None:
            raise ProviderResponseVerificationFailed

        if request.saml_details.relay_state:
            signer = get_signer(request.saml_details.domain)
            redirect_uri = signer.unsign(request.saml_details.relay_state)
            if redirect_uri and redirect_uri in settings.USER_SERVICE_ALLOWED_REDIRECT_URIS:
                response.redirect_uri = redirect_uri

        user_info = authn_response.get_identity()
        email = self._get_value_for_identity_field('Email', user_info)
        first_name = self._get_value_for_identity_field('FirstName', user_info)
        last_name = self._get_value_for_identity_field('LastName', user_info)

        if not self._verify_profile_exists(domain, email):
            raise ProviderResponseVerificationFailed

        identity, created = self.get_identity(email)
        identity.email = email
        full_name = ' '.join([first_name, last_name]).strip()
        if full_name:
            identity.full_name = full_name
        identity.data = json.dumps(user_info)
        return identity

    def _complete_authorization_auth_state(self, request, response):
        parsed_state = parse_state(request.saml_details.auth_state)
        user_id = parsed_state['user_id']
        valid = models.TOTPToken.objects.verify_totp_for_user_id(parsed_state['totp'], user_id)
        if not valid:
            raise InvalidAuthState
        return models.Identity.objects.get(provider=self.type, user_id=user_id)

    def complete_authorization(self, request, response, **kwargs):
        if request.saml_details.HasField('auth_state'):
            return self._complete_authorization_auth_state(request, response)
        else:
            return self._complete_authorization(request, response)

    def finalize_authorization(self, identity, user, request, response):
        # generate an auth_state the user can use to authenticate with the SAML backend once
        response.saml_details.auth_state = get_state_for_user(user, request.saml_details.domain)

    @classmethod
    def get_authorization_url(self, domain, redirect_uri=None, **kwargs):
        sso = get_sso_for_domain(domain)
        saml_client = utils.get_saml_client(domain, sso.metadata)

        if redirect_uri:
            signer = get_signer(domain)
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
