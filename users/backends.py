from protobufs.user_service_pb2 import UserService
import service.control

from . import models


class GoogleAuthenticationBackend(object):

    def authenticate(self, code=None, id_token=None):
        if code and id_token:
            client = service.control.Client('user')
            try:
                response = client.call_action(
                    'complete_authorization',
                    provider=UserService.GOOGLE,
                    oauth_sdk_details={
                        'code': code,
                        'id_token': id_token,
                    },
                )
            except client.CallActionError:
                pass
            else:
                return models.User.objects.get(pk=response.result.user.id)
