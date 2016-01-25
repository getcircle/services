from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.user.actions import authenticate_user_pb2
import service.control

from . import models
from .providers import (
    google,
    okta,
)


class UserBackend(ModelBackend):

    def authenticate(
            self,
            username=None,
            password=None,
            organization=None,
            backend=None,
            **kwargs
        ):
        """Fork of Django's ModelBackend.authenticate method.

        Since we scope user's by organization, we don't require "username" to
        be unique across organizations. We need to pass organization_id
        when fetching the user.

        """
        if backend != authenticate_user_pb2.RequestV1.INTERNAL:
            return None

        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        try:
            user = UserModel.objects.get(**{
                UserModel.USERNAME_FIELD: username,
                'organization_id': organization.id,
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

    def authenticate(self, code=None, id_token=None, organization=None, backend=None, **kwargs):
        if backend != authenticate_user_pb2.RequestV1.GOOGLE:
            return None

        provider = google.Provider()
        try:
            user = provider.authenticate(
                organization=organization,
                code=code,
                id_token=id_token,
            )
        except google.AuthenticationFailed:
            return None

        return user


class OktaAuthenticationBackend(object):

    def authenticate(self, state=None, organization=None, backend=None, **kwargs):
        if backend != authenticate_user_pb2.RequestV1.OKTA:
            return None

        provider = okta.Provider()
        try:
            user = provider.authenticate(
                state=state,
                organization=organization,
            )
        except okta.AuthenticationFailed:
            return None
        return user
