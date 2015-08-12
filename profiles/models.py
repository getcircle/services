from bulk_update.manager import BulkUpdateManager
from common.db import models
from common import utils
from django.contrib.postgres.fields import ArrayField
import django.db
from protobufs.services.profile import containers_pb2 as profile_containers


class Tag(models.UUIDModel, models.TimestampableModel):

    model_to_protobuf_mapping = {'type': 'tag_type'}
    as_dict_value_transforms = {'type': int}

    organization_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=64)
    type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(profile_containers.TagV1.TagTypeV1),
    )

    class Meta:
        unique_together = ('organization_id', 'name', 'type')
        protobuf = profile_containers.TagV1


class Profile(models.UUIDModel, models.TimestampableModel):

    bulk_manager = BulkUpdateManager()

    protobuf_include_fields = ('full_name',)

    organization_id = models.UUIDField()
    user_id = models.UUIDField()
    title = models.CharField(max_length=255, null=True)
    email = models.EmailField()
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    nickname = models.CharField(max_length=64, null=True)
    image_url = models.URLField(max_length=255, null=True)
    birth_date = models.DateField(null=True)
    hire_date = models.DateField(null=True)
    verified = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, through='ProfileTags')
    items = ArrayField(
        ArrayField(models.CharField(max_length=255, null=True), size=2),
        null=True,
    )
    is_admin = models.BooleanField(default=False)
    small_image_url = models.URLField(max_length=255, null=True)

    @property
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

    def to_protobuf(self, protobuf=None, strict=False, extra=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        items = []
        for item in overrides.get('items', self.items) or []:
            container = protobuf.items.add()
            container.key = item[0]
            container.value = item[1]

        contact_methods = []
        for method in overrides.get('contact_methods', self.contact_methods.all()) or []:
            container = protobuf.contact_methods.add()
            method.to_protobuf(container)

        try:
            status = overrides.pop('status', self.profilestatus_set.all().order_by('-created')[0])
        except IndexError:
            status = None

        overrides['items'] = items
        overrides['contact_methods'] = contact_methods
        if status is not None and status.value is not None:
            overrides['status'] = status.as_dict()
        return super(Profile, self).to_protobuf(protobuf, strict=strict, extra=extra, **overrides)

    def update_from_protobuf(self, protobuf):
        items = None
        if protobuf.items:
            items = [(item.key, item.value) for item in protobuf.items if item.key and item.value]

        contact_methods = None
        if protobuf.contact_methods:
            contact_methods = self._update_contact_methods(protobuf.contact_methods)

        status = self._update_status(protobuf)
        return super(Profile, self).update_from_protobuf(
            protobuf,
            items=items,
            contact_methods=contact_methods,
            status=status,
        )

    def _update_status(self, profile_container):
        new_status = None
        try:
            current_status = self.profilestatus_set.all().order_by('-created')[0]
            current_value = current_status.value
        except IndexError:
            current_value = None

        value = profile_container.status.value if profile_container.HasField('status') else None
        if current_value != value:
            instance = ProfileStatus.objects.create(
                profile=self,
                value=value,
                organization_id=self.organization_id,
            )
            if value is not None:
                new_status = instance.to_protobuf()
        return new_status

    def _update_contact_methods(self, methods):
        with django.db.transaction.atomic():
            existing_ids = map(str, self.contact_methods.all().values_list('id', flat=True))
            new_ids = filter(None, [method.id for method in methods])
            to_delete = []
            for method_id in existing_ids:
                if method_id not in new_ids:
                    to_delete.append(method_id)

            if to_delete:
                self.contact_methods.filter(id__in=to_delete).delete()

            for container in methods:
                if container.id:
                    contact_method = ContactMethod.objects.get(
                        id=container.id,
                        profile_id=self.id,
                        organization_id=self.organization_id,
                    )
                    contact_method.update_from_protobuf(container)
                    contact_method.save()
                else:
                    contact_method = ContactMethod.objects.from_protobuf(
                        container,
                        profile_id=self.id,
                        organization_id=self.organization_id,
                    )
                    contact_method.to_protobuf(container)
            return methods

    class Meta:
        unique_together = ('organization_id', 'user_id')
        protobuf = profile_containers.ProfileV1


class ProfileTags(models.TimestampableModel):

    tag = models.ForeignKey(Tag)
    profile = models.ForeignKey(Profile)

    class Meta:
        unique_together = ('tag', 'profile')


class ProfileStatus(models.UUIDModel):

    value = models.TextField(null=True)
    profile = models.ForeignKey(Profile)
    created = models.DateTimeField(auto_now_add=True)
    organization_id = models.UUIDField()

    class Meta:
        index_together = ('profile', 'organization_id', 'created')
        protobuf = profile_containers.ProfileStatusV1


class ContactMethod(models.UUIDModel, models.TimestampableModel):

    model_to_protobuf_mapping = {'type': 'contact_method_type'}
    as_dict_value_transforms = {'type': int}

    profile = models.ForeignKey(Profile, related_name='contact_methods')
    label = models.CharField(max_length=64)
    value = models.CharField(max_length=64)
    type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(
            profile_containers.ContactMethodV1.ContactMethodTypeV1
        ),
    )
    organization_id = models.UUIDField()

    class Meta:
        unique_together = ('profile', 'label', 'value', 'type')
