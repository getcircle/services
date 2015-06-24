from protobufs.services.user import containers_pb2 as user_containers
import service.control

from . import models


class GoogleAuthenticationBackend(object):

    def authenticate(self, code=None, id_token=None, client_type=None):
        if id_token:
            client = service.control.Client('user')
            try:
                response = client.call_action(
                    'complete_authorization',
                    provider=user_containers.IdentityV1.GOOGLE,
                    oauth_sdk_details={
                        'code': code,
                        'id_token': id_token,
                    },
                    client_type=client_type,
                )
            except service.control.CallActionError:
                pass
            else:
                user = models.User.objects.get(pk=response.result.user.id)
                user.new = response.result.new_user
                return user
