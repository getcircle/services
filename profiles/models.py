from bulk_update.manager import BulkUpdateManager
from common.db import models
from common import utils
from django.contrib.postgres.fields import ArrayField
import django.db
from protobufs.services.profile import containers_pb2 as profile_containers
import service.control

from services.utils import should_inflate_field


class Tag(models.UUIDModel, models.TimestampableModel):

    model_to_protobuf_mapping = {'type': 'tag_type'}
    as_dict_value_transforms = {'type': int}

    organization_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=64)
    type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(profile_containers.TagV1.TagTypeV1),
        default=0,
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
    authentication_identifier = models.CharField(max_length=255)

    @property
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

    def get_display_title(self, team):
        display_title = self.title
        if team.name:
            display_title = '%s (%s)' % (self.title, team.name)
        return display_title

    def _get_display_title(self, token):
        response = service.control.call_action(
            service='organization',
            action='get_teams_for_profile_ids',
            client_kwargs={'token': token},
            profile_ids=[str(self.id)],
            fields={'only': ['name']},
        )
        try:
            profile_team = response.result.profiles_teams[0]
        except IndexError:
            return self.title

        return self.get_display_title(profile_team.team)

    def _inflate(self, protobuf, inflations, overrides, token=None):
        if 'contact_methods' not in overrides:
            if should_inflate_field('contact_methods', inflations):
                overrides['contact_methods'] = self.contact_methods.all()

        for method in overrides.pop('contact_methods', None) or []:
            container = protobuf.contact_methods.add()
            method.to_protobuf(container)

        if 'status' not in overrides:
            if should_inflate_field('status', inflations):
                try:
                    overrides['status'] = self.statuses.all().order_by('-created')[0]
                except IndexError:
                    pass

        status = overrides.pop('status', None)
        if status is not None and status.value is not None:
            overrides['status'] = status.as_dict()

        if 'display_title' not in overrides:
            if should_inflate_field('display_title', inflations) and token:
                overrides['display_title'] = self._get_display_title(token)

        return overrides

    def to_protobuf(
            self,
            protobuf=None,
            strict=False,
            extra=None,
            inflations=None,
            token=None,
            **overrides
        ):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)

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

    def _existing_status(self, container):
        instance = ProfileStatus.objects.get(
            organization_id=self.organization_id,
            profile=self,
            pk=container.status.id,
        )
        if container.status.value != instance.value:
            instance.update_from_protobuf(container.status)
            instance.save()
        return instance.to_protobuf()

    def _new_status(self, container):
        try:
            current_status = self.statuses.all().order_by('-created')[0]
            current_value = current_status.value
        except IndexError:
            current_value = None

        value = container.status.value if container.HasField('status') else None
        # support unsetting the current status (creating a stauts with value None, only once)
        if current_value != value:
            instance = ProfileStatus.objects.create(
                profile=self,
                value=value,
                organization_id=self.organization_id,
            )
            if value is not None:
                return instance.to_protobuf()

    def _update_status(self, container):
        next_status = None
        status = container.status
        if status.id:
            next_status = self._existing_status(container)
        else:
            next_status = self._new_status(container)
        return next_status

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
        unique_together = (
            ('organization_id', 'user_id'),
            ('organization_id', 'authentication_identifier'),
        )
        protobuf = profile_containers.ProfileV1


class ProfileTags(models.TimestampableModel):

    tag = models.ForeignKey(Tag)
    profile = models.ForeignKey(Profile)

    class Meta:
        unique_together = ('tag', 'profile')


class ProfileStatus(models.UUIDModel, models.TimestampableModel):

    value = models.TextField(null=True)
    profile = models.ForeignKey(Profile, related_name='statuses')
    organization_id = models.UUIDField()

    def to_protobuf(self, *args, **kwargs):
        protobuf = super(ProfileStatus, self).to_protobuf(*args, **kwargs)
        profile = self.profile.to_protobuf(inflations={'enabled': False})
        protobuf.profile.CopyFrom(profile)
        return protobuf

    class Meta:
        index_together = (('profile', 'organization_id', 'created'), ('value', 'organization_id'))
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
        default=0,
    )
    organization_id = models.UUIDField()

    class Meta:
        unique_together = ('profile', 'label', 'value', 'type')
