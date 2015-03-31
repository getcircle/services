from django.contrib.postgres.fields import ArrayField
from phonenumber_field.modelfields import PhoneNumberField
from protobufs.profile_service_pb2 import ProfileService

from common.db import models


class Tag(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'type': int}

    organization_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=64)
    type = models.SmallIntegerField(
        # NB: protobuf "items" is the opposite order djagno requires
        choices=[(x[1], x[0]) for x in ProfileService.TagType.items()],
    )

    class Meta:
        unique_together = ('organization_id', 'name', 'type')


class Profile(models.UUIDModel, models.TimestampableModel):

    protobuf_include_fields = ('full_name',)

    organization_id = models.UUIDField()
    user_id = models.UUIDField()
    address_id = models.UUIDField(null=True, db_index=True)
    location_id = models.UUIDField(null=True, db_index=True)
    team_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=255)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    nickname = models.CharField(max_length=64, null=True)
    cell_phone = PhoneNumberField(null=True)
    work_phone = PhoneNumberField(null=True)
    image_url = models.URLField(max_length=256, null=True)
    email = models.EmailField()
    birth_date = models.DateField()
    hire_date = models.DateField()
    verified = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, through='ProfileTags')
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


class ProfileTags(models.TimestampableModel):

    tag = models.ForeignKey(Tag)
    profile = models.ForeignKey(Profile)

    class Meta:
        unique_together = ('tag', 'profile')
