import logging

from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)

from users.models import Token as UserToken
from organizations.models import Token as OrganizationToken
from .token import parse_token


AUTHENTICATION_TOKEN_COOKIE_KEY = 'atv1'

logger = logging.getLogger(__name__)


class ServiceTokenAuthentication(BaseAuthentication):
    """Simple token based authentication.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Token ".  For example:

        Authorization: Token 401f7ac837da42b97f613d789819ff93537bee6a

    """

    # TODO this should be a service call
    model = UserToken

    def get_token(self, request):
        logger.info('attempting to get token from header')
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b'token':
            logger.info('no token in header found')
            return None

        logger.info('found token in header')
        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)
        logger.info('valid token header')
        return auth[1]

    def authenticate(self, request):
        token = self.get_token(request)
        if not token:
            return None

        try:
            parsed_token = parse_token(token)
        except Exception:
            raise exceptions.AuthenticationFailed('Invalid token.')
        return self.authenticate_credentials(parsed_token.auth_token)

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        return (token.user, token)

    def authenticate_header(self, request):
        return 'Token'


class ServiceTokenCookieAuthentication(ServiceTokenAuthentication):
    """Simple cookie based token authentication.

    Instead of the token being stored in the header, we look for the token in
    the request cookies.

    """

    def get_token(self, request):
        logger.info('request cookies: %s', request.COOKIES)
        logger.info('token from cookie: %s', request.COOKIES.get(AUTHENTICATION_TOKEN_COOKIE_KEY))
        return request.COOKIES.get(AUTHENTICATION_TOKEN_COOKIE_KEY)


class OrganizationTokenAuthentication(BaseAuthentication):
    """Simple token based authentication for organizations.

    Clients should authenticate by pass the token key in the "Authoriation"
    HTTP header, prepended with the string "OrganizationToken ". For example:

        Authorization: OrganizationToken 401f7ac837da42b97f613d789819ff93537bee6a

    """
    model = OrganizationToken

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or len(auth) < 3 or ' '.join(auth[:2]).lower() != b'organization token':
            return None

        if len(auth) > 3:
            msg = 'Invalid token header.'
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(auth[2])

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related('organization').get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid organization token')

        return (token.organization.to_protobuf(), token)

    def authenticate_header(self, request):
        return 'Organization Token'


def set_authentication_cookie(response, token, secure=True):
    response.set_cookie(
        AUTHENTICATION_TOKEN_COOKIE_KEY,
        value=token,
        domain=settings.AUTHENTICATION_TOKEN_COOKIE_DOMAIN,
        httponly=True,
        secure=secure,
        max_age=settings.AUTHENTICATION_TOKEN_COOKIE_MAX_AGE,
    )


def delete_authentication_cookie(response):
    response.delete_cookie(
        AUTHENTICATION_TOKEN_COOKIE_KEY,
        domain=settings.AUTHENTICATION_TOKEN_COOKIE_DOMAIN,
    )
