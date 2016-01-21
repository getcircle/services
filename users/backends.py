from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from protobufs.services.user import containers_pb2 as user_containers
import service.control

from . import models


class UserBackend(ModelBackend):

    def authenticate(self, username=None, password=None, organization_id=None, **kwargs):
        """Fork of Django's ModelBackend.authenticate method.

        Since we scope user's by organization, we don't require "username" to
        be unique across organizations. We need to pass organization_id
        when fetching the user.

        """
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        try:
            user = UserModel.objects.get(**{
                UserModel.USERNAME_FIELD: username,
                'organization_id': organization_id,
            })
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            UserModel().set_password(password)
        except ValueError:
            pass


class GoogleAuthenticationBackend(object):

    def authenticate(
            self,
            code=None,
            id_token=None,
            client_type=None,
            organization_id=None,
            **kwargs
        ):
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
                organization_id=organization_id,
                **params
            )
        except service.control.CallActionError:
            pass
        else:
            user = models.User.objects.get(pk=response.result.user.id)
            user.new = response.result.new_user
            return user


class OktaAuthenticationBackend(object):

    def authenticate(self, auth_state=None, organization_id=None, **kwargs):
        client = service.control.Client('user')
        try:
            response = client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.OKTA,
                saml_details={
                    'auth_state': auth_state,
                },
                organization_id=organization_id,
            )
        except service.control.CallActionError:
            pass
        else:
            user = models.User.objects.get(pk=response.result.user.id)
            user.new = response.result.new_user
            return user
