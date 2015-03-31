from django.contrib.postgres.fields import ArrayField
import django.db
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
    image_url = models.URLField(max_length=256, null=True)
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

        contact_methods = []
        for method in overrides.get('contact_methods', self.contactmethod_set.all()) or []:
            container = protobuf.contact_methods.add()
            method.to_protobuf(container)

        overrides['items'] = items
        overrides['contact_methods'] = contact_methods
        return super(Profile, self).to_protobuf(protobuf, strict=strict, extra=extra, **overrides)

    def update_from_protobuf(self, protobuf):
        items = None
        if protobuf.items:
            items = [(item.key, item.value) for item in protobuf.items if item.key and item.value]

        contact_methods = None
        if protobuf.contact_methods:
            contact_methods = self._update_contact_methods(protobuf.contact_methods)

        return super(Profile, self).update_from_protobuf(
            protobuf,
            items=items,
            contact_methods=contact_methods,
        )

    def _update_contact_methods(self, methods):
        with django.db.transaction.atomic():
            for container in methods:
                if container.id:
                    contact_method = ContactMethod.objects.get(
                        id=container.id,
                        profile_id=self.id,
                    )
                    contact_method.update_from_protobuf(container)
                    contact_method.save()
                else:
                    contact_method = ContactMethod.objects.from_protobuf(
                        container,
                        profile_id=self.id,
                    )
                    contact_method.to_protobuf(container)
            return methods

    class Meta:
        unique_together = ('organization_id', 'user_id')


class ProfileTags(models.TimestampableModel):

    tag = models.ForeignKey(Tag)
    profile = models.ForeignKey(Profile)

    class Meta:
        unique_together = ('tag', 'profile')


class ContactMethod(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'type': int}

    profile = models.ForeignKey(Profile)
    label = models.CharField(max_length=64)
    value = models.CharField(max_length=64)
    type = models.SmallIntegerField(
        # NB: protobuf "items" is the opposite order djagno requires
        choices=[(x[1], x[0]) for x in ProfileService.ContactMethodType.items()],
    )

    class Meta:
        unique_together = ('profile', 'label', 'value', 'type')
