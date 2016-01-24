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
from protobufs.services.organization.containers import sso_pb2
from timezone_field import TimeZoneField

from services.fields import DescriptionField


class LTreeField(models.Field):

    def db_type(self, connection):
        return 'ltree'


class Organization(models.UUIDModel, models.TimestampableModel):

    class Meta:
        protobuf = organization_containers.OrganizationV1

    name = models.CharField(max_length=64)
    domain = models.CharField(max_length=64, unique=True)
    image_url = models.URLField(max_length=255, null=True)

    def _inflate(self, protobuf, inflations, overrides):
        if 'team_count' not in overrides and utils.should_inflate_field('team_count', inflations):
            overrides['team_count'] = Team.objects.filter(organization_id=self.id).count()

        if 'post_count' not in overrides and utils.should_inflate_field('post_count', inflations):
            # XXX THIS IS REALLY BAD!!! XXX
            from post import models as post_models
            overrides['post_count'] = post_models.Post.objects.filter(
                organization_id=self.id,
            ).count()

        if (
            'profile_count' not in overrides and
            utils.should_inflate_field('profile_count', inflations)
        ):
            from profiles import models as profile_models
            overrides['profile_count'] = profile_models.Profile.objects.filter(
                organization_id=self.id,
            ).count()

        if (
            'location_count' not in overrides and
            utils.should_inflate_field('location_count', inflations)
        ):
            overrides['location_count'] = Location.objects.filter(organization_id=self.id).count()

    def to_protobuf(self, protobuf=None, inflations=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides)
        return super(Organization, self).to_protobuf(protobuf, inflations=inflations, **overrides)


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

    def to_protobuf(self, protobuf=None, token=None, fields=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)

        if (
            utils.should_populate_field('description', fields) and
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

        if (
            'profile_count' not in overrides and
            utils.should_populate_field('profile_count', fields)
        ):
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

        if utils.should_populate_field('display_name', fields):
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

        return super(Team, self).to_protobuf(protobuf, fields=fields, **overrides)


class TeamStatus(models.UUIDModel, models.TimestampableModel):

    value = models.TextField(null=True)
    team = models.ForeignKey(Team)
    organization_id = models.UUIDField(editable=False)
    by_profile_id = models.UUIDField(editable=False)

    class Meta:
        index_together = ('team', 'organization_id', 'created')


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
        if (
            'profile_count' not in overrides and
            utils.should_inflate_field('profile_count', inflations)
        ):
            overrides['profile_count'] = self.members.count()

        if self.description and self.description.by_profile_id:
            if token and utils.should_inflate_field('description.by_profile_id', inflations):
                by_profile = service.control.get_object(
                    'profile',
                    'get_profile',
                    client_kwargs={'token': token},
                    return_object='profile',
                    profile_id=str(self.description.by_profile_id),
                    inflations={'disabled': True},
                )
                self.description.by_profile.CopyFrom(by_profile)

    def to_protobuf(self, protobuf=None, inflations=None, token=None, **overrides):
        protobuf = self.new_protobuf_container(protobuf)
        self._inflate(protobuf, inflations, overrides, token)
        return super(Location, self).to_protobuf(protobuf, inflations=inflations, **overrides)


class LocationMember(models.UUIDModel):

    location = models.ForeignKey(Location, related_name='members')
    profile_id = models.UUIDField()
    organization = models.ForeignKey(Organization, editable=False)
    added_by_profile_id = models.UUIDField(editable=False, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile_id', 'location')
        index_together = (
            ('profile_id', 'organization'),
            ('location', 'organization'),
        )


class SSO(models.UUIDModel, models.Model):

    as_dict_value_transforms = {'provider': int}

    organization = models.OneToOneField(Organization, related_name='sso')
    details = models.ProtobufField(
        protobuf_classes=[
            sso_pb2.SAMLDetailsV1,
            sso_pb2.GoogleDetailsV1,
        ],
    )
    provider = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(
            sso_pb2.ProviderV1,
        ),
    )

    class Meta:
        protobuf = sso_pb2.SSOV1

    def to_protobuf(self, *args, **kwargs):
        if self.details and self.provider == sso_pb2.OKTA:
            kwargs.update({'saml': protobuf_to_dict(self.details)})
        elif self.details and self.provider == sso_pb2.GOOGLE:
            kwargs.update({'google': protobuf_to_dict(self.details)})
        return super(SSO, self).to_protobuf(*args, **kwargs)


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
        protobuf_classes=[
            integration_pb2.GoogleGroupDetailsV1,
            integration_pb2.SlackSlashCommandDetailsV1,
            integration_pb2.SlackWebApiDetailsV1,
        ],
        null=True,
    )
    provider_uid = models.CharField(max_length=255, unique=True, null=True)

    def to_protobuf(self, *args, **kwargs):
        if self.details and self.type == integration_pb2.GOOGLE_GROUPS:
            kwargs.update({'google_groups': protobuf_to_dict(self.details)})
        elif self.details and self.type == integration_pb2.SLACK_SLASH_COMMAND:
            kwargs.update({'slack_slash_command': protobuf_to_dict(self.details)})
        elif self.details and self.type == integration_pb2.SLACK_WEB_API:
            kwargs.update({'slack_web_api': protobuf_to_dict(self.details)})
        return super(Integration, self).to_protobuf(*args, **kwargs)
