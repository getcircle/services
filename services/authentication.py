from rest_framework import exceptions
from rest_framework.authentication import (
    get_authorization_header,
    TokenAuthentication,
)

from .token import parse_token


class ServiceTokenAuthentication(TokenAuthentication):

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

        token = parse_token(auth[1])
        return self.authenticate_credentials(token.auth_token)
