import binascii
import os

from common.db import models
from common import utils
from django.contrib.postgres.fields import ArrayField
from mptt.models import (
    MPTTModel,
    TreeForeignKey,
)
from mptt.managers import TreeManager
from protobuf_to_dict import protobuf_to_dict
import service.control

from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.organization.containers import integration_pb2
from timezone_field import TimeZoneField

from services.fields import DescriptionField
from services.utils import should_inflate_field


class LTreeField(models.Field):

    def db_type(self, connection):
        return 'ltree'


class Organization(models.UUIDModel, models.TimestampableModel):

    class Meta:
        protobuf = organization_containers.OrganizationV1

    name = models.CharField(max_length=64)
    domain = models.CharField(max_length=64, unique=True)
    image_url = models.URLField(max_length=255, null=True)


class ReportingStructure(MPTTModel, models.TimestampableModel):

    trees = TreeManager()

    profile_id = models.UUIDField(primary_key=True)
    manager = TreeForeignKey('self', null=True, related_name='reports', db_index=True)
    organization = models.ForeignKey(Organization, db_index=True, editable=False)
    added_by_profile_id = models.UUIDField(null=True, editable=False)

    class MPTTMeta:
        parent_attr = 'manager'


class Team(models.UUIDModel, models.TimestampableModel):

    name = models.CharField(max_length=255, null=True)
    description = DescriptionField(null=True)
    manager_profile_id = models.UUIDField(editable=False)
    created_by_profile_id = models.UUIDField(editable=False, null=True)
    organization = models.ForeignKey(Organization, editable=False)
    image_url = models.URLField(max_length=255, null=True)

    class Meta:
        index_together = ('manager_profile_id', 'organization')
        protobuf = organization_containers.TeamV1

    def get_description(self):
        return self.description or {}

    def _update_status(self, team_container, by_profile_id):
        new_status = None
        try:
            current_status = self.teamstatus_set.all().order_by('-created')[0]
            current_value = current_status.value
        except IndexError:
            current_value = None

        value = team_container.status.value if team_container.HasField('status') else None
        if current_value != value:
            instance = TeamStatus.objects.create(
                team=self,
                value=value,
                organization_id=self.organization_id,
                by_profile_id=by_profile_id,
            )
            if value is not None:
                new_status = instance.to_protobuf()
        return new_status

    def update_from_protobuf(self, protobuf, by_profile_id):
        status = self._update_status(protobuf, by_profile_id)
        return super(Team, self).update_from_protobuf(protobuf, status=status)

    def to_protobuf(self, protobuf=None, strict=False, extra=None, token=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        try:
            status = overrides.pop('status')
        except KeyError:
            try:
                status = self.teamstatus_set.all().order_by('-created')[0]
            except IndexError:
                status = None

        if status is not None and status.value is not None:
            status_dict = status.as_dict()
            if token:
                by_profile = service.control.get_object(
                    'profile',
                    'get_profile',
                    client_kwargs={'token': token},
                    return_object='profile',
                    profile_id=str(status.by_profile_id),
                )
                status_dict['by_profile'] = protobuf_to_dict(by_profile)
            overrides['status'] = status_dict

        if (
            'description' not in overrides and
            self.description and
            self.description.by_profile_id
        ):
            if token:
                by_profile = service.control.get_object(
                    'profile',
                    'get_profile',
                    client_kwargs={'token': token},
                    return_object='profile',
                    profile_id=str(self.description.by_profile_id),
                )
                self.description.by_profile.CopyFrom(by_profile)

        if 'profile_count' not in overrides:
            manager = ReportingStructure.objects.get(
                pk=self.manager_profile_id,
                organization_id=self.organization_id,
            )
            descendant_count = manager.get_descendant_count()
            # NB: We want to include the manager in the profile_count
            overrides['profile_count'] = descendant_count + 1
            if descendant_count > 0:
                children = manager.get_children()
                overrides['child_team_count'] = len(
                    [child for child in children if child.get_descendant_count() > 0]
                )

        if not self.name and 'name' not in overrides:
            # XXX REALLY BAD!!! XXX
            from profiles import models as profile_models
            try:
                manager_name = profile_models.Profile.objects.filter(
                    organization_id=self.organization_id,
                    id=self.manager_profile_id,
                ).values_list('first_name', flat=True)[0]
            except IndexError:
                pass
            else:
                overrides['display_name'] = '%s\'s Nameless Team' % (manager_name,)
        elif self.name:
            overrides['display_name'] = self.name
        elif 'name' in overrides:
            overrides['display_name'] = overrides['name']

        return super(Team, self).to_protobuf(protobuf, strict=strict, extra=extra, **overrides)


class TeamStatus(models.UUIDModel):

    value = models.TextField(null=True)
    team = models.ForeignKey(Team)
    created = models.DateTimeField(auto_now_add=True)
    organization_id = models.UUIDField(editable=False)
    by_profile_id = models.UUIDField(editable=False)

    class Meta:
        index_together = ('team', 'organization_id', 'created')
        protobuf = organization_containers.TeamStatusV1


class Location(models.UUIDModel, models.TimestampableModel):

    organization = models.ForeignKey(Organization, db_index=True, editable=False)
    name = models.CharField(max_length=64)
    address_1 = models.CharField(max_length=128)
    address_2 = models.CharField(max_length=128, null=True)
    city = models.CharField(max_length=64)
    region = models.CharField(max_length=64)
    postal_code = models.CharField(max_length=64)
    # ISO 3166-1 alpha-3
    country_code = models.CharField(max_length=3)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    timezone = TimeZoneField()
    image_url = models.URLField(max_length=255, null=True)
    description = DescriptionField(null=True)
    established_date = models.DateField(null=True)
    points_of_contact_profile_ids = ArrayField(models.UUIDField(), null=True)

    class Meta:
        unique_together = ('name', 'organization')
        protobuf = organization_containers.LocationV1

    def update_from_protobuf(self, protobuf):
        points_of_contact_profile_ids = [profile.id for profile in protobuf.points_of_contact]
        return super(Location, self).update_from_protobuf(
            protobuf,
            points_of_contact_profile_ids=points_of_contact_profile_ids,
        )

    def _inflate(self, protobuf, inflations, overrides, token):
        if 'profile_count' not in overrides and should_inflate_field('profile_count', inflations):
            overrides['profile_count'] = self.members.count()

        if self.description and self.description.by_profile_id:
            if token and should_inflate_field('description.by_profile_id', inflations):
                by_profile = service.control.get_object(
                    'profile',
                    'get_profile',
                    client_kwargs={'token': token},
                    return_object='profile',
                    profile_id=str(self.description.by_profile_id),
                    inflations={'enabled': False},
                )
                self.description.by_profile.CopyFrom(by_profile)

    def to_protobuf(
            self,
            protobuf=None,
            strict=False,
            extra=None,
            token=None,
            inflations=None,
            **overrides
        ):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)
        return super(Location, self).to_protobuf(protobuf, strict=strict, extra=extra, **overrides)


class LocationMember(models.UUIDModel):

    location = models.ForeignKey(Location, related_name='members')
    profile_id = models.UUIDField()
    organization = models.ForeignKey(Organization, editable=False)
    added_by_profile_id = models.UUIDField(editable=False, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('profile_id', 'organization'),
            ('location', 'organization'),
        )


class Token(models.UUIDModel):

    key = models.CharField(max_length=40)
    organization = models.ForeignKey(Organization, related_name='auth_token')
    requested_by_user_id = models.UUIDField(null=True)
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __unicode__(self):
        return self.key


class SSO(models.UUIDModel, models.Model):

    organization = models.ForeignKey(Organization, related_name='sso', db_index=True)
    metadata_url = models.CharField(max_length=255, null=True)
    metadata = models.TextField(null=True)

    class Meta:
        protobuf = organization_containers.SSOV1


class Integration(models.UUIDModel, models.Model):

    model_to_protobuf_mapping = {'type': 'integration_type'}
    as_dict_value_transforms = {'type': int}

    class Meta:
        protobuf = integration_pb2.IntegrationV1
        unique_together = ('organization', 'type')

    organization = models.ForeignKey(Organization, db_index=True)
    type = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(
            integration_pb2.IntegrationTypeV1,
        ),
    )
    details = models.ProtobufField(
        protobuf_classes=[integration_pb2.GoogleGroupDetailsV1],
        null=True,
    )

    def to_protobuf(self, *args, **kwargs):
        if self.details and self.type == integration_pb2.GOOGLE_GROUPS:
            kwargs.update({'google_groups': protobuf_to_dict(self.details)})
        return super(Integration, self).to_protobuf(*args, **kwargs)
