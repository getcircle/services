from phonenumber_field.modelfields import PhoneNumberField

from common.db import models


class Identity(models.TimestampableModel):

    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    email = models.EmailField()
    phone_number = PhoneNumberField(null=True)
    user = models.ForeignKey('users.User')
