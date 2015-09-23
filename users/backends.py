from protobufs.services.user.actions import authenticate_user_pb2
from protobufs.services.user import containers_pb2 as user_containers
import service.control

from .providers.base import parse_state_token

from . import models


class GoogleAuthenticationBackend(object):

    def authenticate(self, code=None, id_token=None, client_type=None):
        client = service.control.Client('user')
        params = {}
        if id_token:
            params['oauth_sdk_details'] = {
                'code': code,
                'id_token': id_token,
            }
        else:
            params['oauth2_details'] = {
                'code': code,
            }

        try:
            response = client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.GOOGLE,
                client_type=client_type,
                **params
            )
        except service.control.CallActionError:
            pass
        else:
            user = models.User.objects.get(pk=response.result.user.id)
            user.new = response.result.new_user
            return user


class SAMLAuthenticationBackend(object):

    def authenticate(self, auth_state=None):
        client = service.control.Client('user')
        try:
            response = client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.SAML,
                saml_details={
                    'auth_state': auth_state,
                },
            )
        except service.control.CallActionError:
            pass
        else:
            user = models.User.objects.get(pk=response.result.user.id)
            user.new = response.result.new_user
            return user
