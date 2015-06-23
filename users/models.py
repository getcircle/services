import binascii
import os
from common.db import models
from common import utils

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
)
from phonenumber_field.modelfields import PhoneNumberField
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.user.containers import token_pb2
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
    protobuf_exclude_fields = ['password']

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

    class Meta:
        protobuf = user_containers.UserV1


class Token(models.UUIDModel):

    key = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey(User, related_name='auth_token', db_index=True)
    client_type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(token_pb2.ClientTypeV1),
    )
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __unicode__(self):
        return self.key


class TOTPToken(models.UUIDModel, models.TimestampableModel):

    user = models.OneToOneField(User)
    # XXX not sure if this needs to be encrypted
    token = models.CharField(max_length=16, default=pyotp.random_base32)


class Identity(models.UUIDModel, models.TimestampableModel):

    # TODO: We should be using user_containers.ProviderV1.items() and reversing
    # the tuples within the list
    providers = (
        (user_containers.IdentityV1.LINKEDIN, 'LinkedIn'),
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


class Device(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'provider': int}

    user = models.ForeignKey(User)
    notification_token = models.CharField(max_length=255, null=True)
    platform = models.CharField(max_length=255)
    os_version = models.CharField(max_length=255)
    app_version = models.CharField(max_length=255)
    device_uuid = models.CharField(max_length=255, db_index=True)
    language_preference = models.CharField(max_length=16, default='en')
    provider = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(user_containers.DeviceV1.ProviderV1),
        null=True,
    )
    last_token_id = models.UUIDField(null=True)

    class Meta:
        index_together = ('user', 'last_token_id')


class AccessRequest(models.UUIDModel, models.TimestampableModel):

    user = models.OneToOneField(User)
