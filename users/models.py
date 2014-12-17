from common.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
)
import service.control


class UserManager(BaseUserManager):

    def _create_user(
        self,
        primary_email,
        password,
        is_active,
        is_admin,
        **extra_fields
    ):
        primary_email = self.normalize_email(primary_email)
        user = self.model(
            primary_email=primary_email,
            is_active=is_active,
            is_admin=is_admin,
            **extra_fields
        )
        if not password:
            password = self.make_random_password()

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, primary_email, password=None, **extra_fields):
        return self._create_user(
            primary_email,
            password,
            True,
            False,
            **extra_fields
        )

    def create_superuser(self, primary_email, password, **extra_fields):
        return self._create_user(
            primary_email,
            password,
            True,
            True,
            **extra_fields
        )


class User(AbstractBaseUser, models.UUIDModel, models.TimestampableModel):

    USERNAME_FIELD = 'primary_email'

    objects = UserManager()

    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    primary_email = models.EmailField(unique=True)

    def get_identities(self):
        if not hasattr(self, '_identities'):
            client = service.control.Client('identity')
            _, response = client.call_action(
                'get_identities',
                user_id=self.id.hex,
            )
            self._identities = response.identities
        return self._identities

    def get_an_identity(self):
        identities = self.get_identities()
        if identities:
            return identities[0]

    def get_full_name(self):
        full_name = 'unnamed'
        identity = self.get_an_identity()
        if identity:
            full_name = identity.email
        return full_name

    def get_short_name(self):
        return self.get_full_name()

    @property
    def is_staff(self):
        return self.is_admin

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        return True
