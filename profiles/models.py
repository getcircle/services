from bulk_update.manager import BulkUpdateManager
from common.db import models
from common import utils
from django.contrib.postgres.fields import ArrayField
import django.db
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.profile import containers_pb2 as profile_containers
import service.control


class ProfileManager(models.Manager):

    def create(self, *args, **kwargs):
        profile = super(ProfileManager, self).create(*args, **kwargs)
        # XXX fix this later
        from post import models as post_models
        post_models.Collection.objects.create(
            owner_type=post_containers.CollectionV1.PROFILE,
            owner_id=profile.id,
            organization_id=profile.organization_id,
            is_default=True,
            position=0,
        )
        return profile

    def bulk_create(self, *args, **kwargs):
        profiles = super(ProfileManager, self).bulk_create(*args, **kwargs)
        # XXX fix this later
        from post import models as post_models
        collections = []
        for profile in profiles:
            collection = post_models.Collection(
                owner_type=post_containers.CollectionV1.PROFILE,
                owner_id=profile.id,
                organization_id=profile.organization_id,
                is_default=True,
                position=0,
            )
            collections.append(collection)
        post_models.Collection.objects.bulk_create(collections)
        return profiles


class Profile(models.UUIDModel, models.TimestampableModel):

    bulk_manager = BulkUpdateManager()
    objects = ProfileManager()

    protobuf_include_fields = ('full_name',)
    as_dict_value_transforms = {'status': int}

    organization_id = models.UUIDField()
    user_id = models.UUIDField()
    title = models.CharField(max_length=255, null=True)
    email = models.EmailField()
    bio = models.TextField(null=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    nickname = models.CharField(max_length=64, null=True)
    image_url = models.URLField(max_length=255, null=True)
    birth_date = models.DateField(null=True)
    hire_date = models.DateField(null=True)
    verified = models.BooleanField(default=False)
    items = ArrayField(
        ArrayField(models.CharField(max_length=255, null=True), size=2),
        null=True,
    )
    is_admin = models.BooleanField(default=False)
    small_image_url = models.URLField(max_length=255, null=True)
    authentication_identifier = models.CharField(max_length=255)
    sync_source_id = models.CharField(max_length=255, null=True)
    status = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(
            profile_containers.ProfileV1.StatusV1,
        ),
        default=0,
    )

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
            if utils.should_inflate_field('contact_methods', inflations):
                overrides['contact_methods'] = self.contact_methods.all()

        for method in overrides.pop('contact_methods', None) or []:
            container = protobuf.contact_methods.add()
            method.to_protobuf(container)

        if 'display_title' not in overrides:
            if utils.should_inflate_field('display_title', inflations) and token:
                overrides['display_title'] = self._get_display_title(token)

        return overrides

    def to_protobuf(self, protobuf=None, inflations=None, token=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)

        items = []
        for item in overrides.get('items', self.items) or []:
            container = protobuf.items.add()
            container.key = item[0]
            container.value = item[1]

        overrides['items'] = items
        return super(Profile, self).to_protobuf(protobuf, inflations=inflations, **overrides)

    def update_from_protobuf(self, protobuf):
        items = None
        if protobuf.items:
            items = [(item.key, item.value) for item in protobuf.items if item.key and item.value]

        contact_methods = self._update_contact_methods(protobuf.contact_methods)
        return super(Profile, self).update_from_protobuf(
            protobuf,
            items=items,
            contact_methods=contact_methods,
        )

    def _update_contact_methods(self, methods):
        with django.db.transaction.atomic():
            existing_ids = map(str, self.contact_methods.all().values_list('id', flat=True))
            new_ids = filter(None, [method.id for method in methods])
            to_delete = []
            for method_id in existing_ids:
                if method_id not in new_ids:
                    to_delete.append(method_id)

            if to_delete:
                self.contact_methods.filter(
                    id__in=to_delete,
                    organization_id=self.organization_id,
                ).delete()

            # TODO should be bulk creating and updating these
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


class ProfileStatus(models.UUIDModel, models.TimestampableModel):

    value = models.TextField(null=True)
    profile = models.ForeignKey(Profile, related_name='statuses')
    organization_id = models.UUIDField()

    def to_protobuf(self, *args, **kwargs):
        protobuf = super(ProfileStatus, self).to_protobuf(*args, **kwargs)
        profile = self.profile.to_protobuf(inflations={'disabled': True})
        protobuf.profile.CopyFrom(profile)
        return protobuf

    class Meta:
        index_together = (('profile', 'organization_id', 'created'), ('value', 'organization_id'))


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


class SyncSettings(models.TimestampableModel):

    organization_id = models.UUIDField(primary_key=True)
    mappings = models.TextField()
    validate_fields = models.TextField(null=True)
    endpoint = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
