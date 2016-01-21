import binascii
import os
from common.db import models
from common import utils

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
)
from django.conf import settings
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.user.containers import token_pb2
import pyotp


class UserManager(BaseUserManager, models.CommonManager):

    def _create_user(
        self,
        organization_id,
        primary_email,
        password,
        is_active,
        is_admin,
        **extra_fields
    ):
        primary_email = self.normalize_email(primary_email)
        user = self.model(
            organization_id=organization_id,
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

    def create_user(self, organization_id, primary_email, password=None, **extra_fields):
        return self._create_user(
            organization_id=organization_id,
            primary_email=primary_email,
            password=password,
            is_active=True,
            is_admin=False,
            **extra_fields
        )

    def create_superuser(self, organization_id, primary_email, password, **extra_fields):
        return self._create_user(
            organization_id=organization_id,
            primary_email=primary_email,
            password=password,
            is_active=True,
            is_admin=True,
            **extra_fields
        )


class User(AbstractBaseUser, models.UUIDModel, models.TimestampableModel):

    USERNAME_FIELD = 'primary_email'
    protobuf_exclude_fields = ('password',)

    objects = UserManager()

    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    primary_email = models.EmailField()
    organization_id = models.UUIDField(db_index=True)

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
        unique_together = ('primary_email', 'organization_id')


class Token(models.UUIDModel):

    key = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey(User, related_name='auth_token')
    client_type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(token_pb2.ClientTypeV1),
    )
    created = models.DateTimeField(auto_now_add=True)
    organization_id = models.UUIDField()

    class Meta:
        index_together = ('user', 'organization_id')

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __unicode__(self):
        return self.key


class TOTPTokenManager(models.CommonManager):

    def _get_totp_code(self, token):
        totp_code = str(pyotp.TOTP(token, interval=settings.USER_SERVICE_TOTP_INTERVAL).now())
        if len(totp_code) < 6:
            totp_code = '0%s' % (totp_code,)
        return totp_code

    def _token_for_user(self, user):
        # clear any previously created tokens
        self.filter(user_id=user.id, organization_id=user.organization_id).delete()
        return self.create(user_id=user.id, organization_id=user.organization_id)

    def totp_for_user(self, user):
        token = self._token_for_user(user)
        return self._get_totp_code(token.token)

    def get_totp_for_user_id(self, user_id):
        token = self.get(user_id=user_id)
        return self._get_totp_code(token.token)

    def verify_totp_for_user_id(self, input_totp, user_id):
        totp = self.get_totp_for_user_id(user_id)
        if totp != input_totp:
            return False
        else:
            # clear out the token so we can only use it once
            self.filter(user_id=user_id).delete()
            return True


class TOTPToken(models.UUIDModel, models.TimestampableModel):

    objects = TOTPTokenManager()

    user = models.OneToOneField(User)
    token = models.CharField(max_length=16, default=pyotp.random_base32)
    organization_id = models.UUIDField()

    class Meta:
        index_together = ('user', 'organization_id')


class Identity(models.UUIDModel, models.TimestampableModel):

    user = models.ForeignKey(User)
    provider = models.PositiveSmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(user_containers.IdentityV1.ProviderV1),
    )
    full_name = models.CharField(max_length=255, null=True)
    email = models.EmailField()
    data = models.TextField(null=True)
    provider_uid = models.CharField(max_length=255)
    access_token = models.CharField(max_length=255, null=True)
    refresh_token = models.CharField(max_length=255, null=True)
    expires_at = models.PositiveIntegerField(null=True)
    organization_id = models.UUIDField()

    def to_protobuf(self, *args, **kwargs):
        # override "provider" to prevent casting as a string
        return super(Identity, self).to_protobuf(provider=self.provider, *args, **kwargs)

    class Meta:
        unique_together = ('user', 'provider', 'provider_uid', 'organization_id')


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
    organization_id = models.UUIDField()

    class Meta:
        index_together = ('user', 'last_token_id', 'organization_id')
