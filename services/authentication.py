from rest_framework import exceptions
from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)

from users.models import Token as UserToken
from organizations.models import Token as OrganizationToken
from .token import parse_token


class ServiceTokenAuthentication(BaseAuthentication):
    """
    Simple token based authentication.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Token ".  For example:

        Authorization: Token 401f7ac837da42b97f613d789819ff93537bee6a
    """

    # TODO this should be a service call
    model = UserToken

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'token':
            return None

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = parse_token(auth[1])
        except Exception:
            raise exceptions.AuthenticationFailed('Invalid token.')
        return self.authenticate_credentials(token.auth_token)

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


class OrganizationTokenAuthentication(BaseAuthentication):
    """
    Simple token based authentication for organizations.

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
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid organization token')

        return (token.organization, token)

    def authenticate_header(self, request):
        return 'Organization Token'
