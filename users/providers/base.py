import json
import logging

from cryptography.fernet import (
    Fernet,
    InvalidToken,
    MultiFernet,
)
from django.conf import settings
from django.utils.crypto import get_random_string
from itsdangerous import (
    BadSignature,
    TimestampSigner,
)

from .. import models

logger = logging.getLogger(__name__)

CSRF_KEY_LENGTH = 32


def get_state_signer(provider):
    return TimestampSigner(settings.SECRET_KEY, salt=str(provider))


def get_state_token(provider, payload):
    payload['csrftoken'] = get_random_string(CSRF_KEY_LENGTH)
    signer = get_state_signer(provider)
    encrypter = MultiFernet(map(Fernet, settings.SECRET_ENCRYPTION_KEYS))
    token = encrypter.encrypt(json.dumps(payload))
    return signer.sign(token)


def parse_state_token(provider, token):
    payload = None
    signer = get_state_signer(provider)
    crypt = MultiFernet(map(Fernet, settings.SECRET_ENCRYPTION_KEYS))
    try:
        encrypted_token = signer.unsign(token, max_age=settings.USER_SERVICE_STATE_MAX_AGE)
        payload = json.loads(
            crypt.decrypt(encrypted_token, ttl=settings.USER_SERVICE_STATE_MAX_AGE)
        )
    except (BadSignature, InvalidToken, ValueError) as e:
        logger.error('failed to decrypt state payload: %s', e)
        payload = None
    return payload


class ExchangeError(Exception):
    """Exception raised when there is an error exchanging authorization code for access token"""

    def __init__(self, response, *args, **kwargs):
        self.response = response
        super(ExchangeError, self).__init__(*args, **kwargs)


class ProviderAPIError(ExchangeError):
    """Exception raised when a provider API call fails"""


class MissingRequiredProfileFieldError(Exception):
    """Exception raised when a required profile field is missing"""


class ImproperlyConfiguredError(Exception):
    """Exception raised when a provider isn't configured correctly"""


class BaseProvider(object):

    type = None
    csrf_exempt = False
    exception_to_error_map = {}

    def __init__(self, token):
        self.token = token
        if self.type is None:
            raise ImproperlyConfiguredError

    def get_identity(self, provider_uid):
        new = False
        identity = models.Identity.objects.get_or_none(
            provider_uid=provider_uid,
            provider=self.type,
        )
        if identity is None:
            new = True
            identity = models.Identity(provider=self.type, provider_uid=provider_uid)
        return identity, new

    @classmethod
    def get_authorization_url(self, token=None, **kwargs):
        raise NotImplementedError('Subclasses must override this method')

    def complete_authorization(self, request, response):
        raise NotImplementedError('Subclasses must override this method')

    def finalize_authorization(self, identity, user, request, response):
        pass

    def _extract_required_profile_field(self, profile, field_name, alias=None):
        try:
            value = profile[field_name]
        except KeyError:
            alias = alias or field_name
            raise MissingRequiredProfileFieldError(alias)
        return value
