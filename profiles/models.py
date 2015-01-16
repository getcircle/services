from phonenumber_field.modelfields import PhoneNumberField

from common.db import models


class Tag(models.UUIDModel, models.TimestampableModel):

    organization_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=64)

    class Meta:
        unique_together = ('organization_id', 'name')


class Profile(models.UUIDModel, models.TimestampableModel):

    protobuf_include_fields = ('full_name',)

    organization_id = models.UUIDField()
    user_id = models.UUIDField()
    address_id = models.UUIDField()
    team_id = models.UUIDField()
    title = models.CharField(max_length=64)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    cell_phone = PhoneNumberField(null=True)
    work_phone = PhoneNumberField(null=True)
    image_url = models.CharField(max_length=256, null=True)
    email = models.EmailField()
    birth_date = models.DateField()
    hire_date = models.DateField()
    verified = models.BooleanField(default=False)

    tags = models.ManyToManyField(Tag, through='ProfileTags')

    @property
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

    class Meta:
        unique_together = ('organization_id', 'user_id')


class ProfileTags(models.TimestampableModel):

    tag = models.ForeignKey(Tag)
    profile = models.ForeignKey(Profile)
