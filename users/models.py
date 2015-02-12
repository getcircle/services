from common.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
)
from phonenumber_field.modelfields import PhoneNumberField
from protobufs.user_service_pb2 import UserService
import pyotp


class UserManager(BaseUserManager, models.CommonManager):

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
    phone_number = PhoneNumberField(null=True, unique=True)
    phone_number_verified = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self.new = False

    def get_full_name(self):
        return self.primary_email

    def get_short_name(self):
        return self.primary_email

    @property
    def is_staff(self):
        return self.is_admin

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        return True


class TOTPToken(models.UUIDModel, models.TimestampableModel):

    # XXX switch to 1-1 field
    user = models.ForeignKey(User, unique=True)
    # XXX not sure if this needs to be encrypted
    token = models.CharField(max_length=16, default=pyotp.random_base32)


class Identity(models.UUIDModel, models.TimestampableModel):

    providers = (
        (UserService.LINKEDIN, 'LinkedIn'),
    )

    user = models.ForeignKey(User)
    provider = models.PositiveSmallIntegerField(choices=providers)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255, null=True)
    provider_uid = models.CharField(max_length=255)
    expires_at = models.PositiveIntegerField()
    data = models.TextField(null=True)

    def to_protobuf(self, *args, **kwargs):
        # override "provider" to prevent casting as a string
        return super(Identity, self).to_protobuf(provider=self.provider, *args, **kwargs)

    class Meta:
        unique_together = (('user', 'provider'), ('provider', 'provider_uid'))
