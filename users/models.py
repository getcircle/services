from common.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
)


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
