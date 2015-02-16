from django.contrib.postgres.fields import ArrayField
from phonenumber_field.modelfields import PhoneNumberField

from common.db import models


class Skill(models.UUIDModel, models.TimestampableModel):

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
    skills = models.ManyToManyField(Skill, through='ProfileSkills')
    items = ArrayField(
        ArrayField(models.CharField(max_length=256, null=True), size=2),
        null=True,
    )
    about = models.TextField(null=True)

    @property
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

    def to_protobuf(self, protobuf, strict=False, extra=None, **overrides):
        items = []
        for item in overrides.get('items', self.items) or []:
            container = protobuf.items.add()
            container.key = item[0]
            container.value = item[1]
        overrides['items'] = items
        return super(Profile, self).to_protobuf(protobuf, strict=strict, extra=extra, **overrides)

    def update_from_protobuf(self, protobuf):
        items = None
        if protobuf.items:
            items = [(item.key, item.value) for item in protobuf.items if item.key and item.value]
        return super(Profile, self).update_from_protobuf(protobuf, items=items)

    class Meta:
        unique_together = ('organization_id', 'user_id')


class ProfileSkills(models.TimestampableModel):

    skill = models.ForeignKey(Skill)
    profile = models.ForeignKey(Profile)

    class Meta:
        unique_together = ('skill', 'profile')
