from django.contrib.auth import hashers

from common.db import models

from . import HASH_ALGORITHM


class Credential(models.UUIDModel, models.TimestampableModel):

    user = models.ForeignKey('users.User', unique=True)
    password = models.CharField(
        null=True,
        max_length=255,
    )

    def set_password(self, new_password, commit=True):
        self.password = hashers.make_password(
            new_password,
            hasher=HASH_ALGORITHM,
        )
        if commit:
            self.save()

    def check_password(self, password):
        return hashers.check_password(
            password,
            self.password,
            preferred=HASH_ALGORITHM,
        )
