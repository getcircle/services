import binascii
import os
from common.db import models
from common import utils
from protobuf_to_dict import protobuf_to_dict

from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.organization.containers import integration_pb2
from timezone_field import TimeZoneField


class LTreeField(models.Field):

    def db_type(self, connection):
        return 'ltree'


class Organization(models.UUIDModel, models.TimestampableModel):

    class Meta:
        protobuf = organization_containers.OrganizationV1

    name = models.CharField(max_length=64)
    domain = models.CharField(max_length=64, unique=True)
    image_url = models.URLField(max_length=255, null=True)


class Team(models.UUIDModel, models.TimestampableModel):

    def __init__(self, *args, **kwargs):
        super(Team, self).__init__(*args, **kwargs)
        self._path = None

    protobuf_include_fields = ('department',)

    name = models.CharField(max_length=255)
    owner_id = models.UUIDField(db_index=True, editable=False)
    organization = models.ForeignKey(Organization, db_index=True, editable=False)
    path = LTreeField(null=True, db_index=True, editable=False)

    def get_path(self, path_dict=None):
        if self._path is None:
            path_parts = self.path.split('.')
            if path_dict is None:
                path = Team.objects.filter(pk__in=path_parts).values(
                    'id',
                    'name',
                    'owner_id',
                )
            else:
                path = filter(None, [path_dict.get(part) for part in path_parts])

            # XXX see if we can have the client handle this for us
            for item in path:
                item['id'] = str(item['id'])
                item['owner_id'] = str(item['owner_id'])
            self._path = path
        return self._path

    @property
    def department(self):
        department_title = None
        path = self.get_path()
        try:
            department_title = path[1]['name']
        except IndexError:
            pass
        return department_title

    class Meta:
        unique_together = ('name', 'organization')
        protobuf = organization_containers.TeamV1


class Address(models.UUIDModel, models.TimestampableModel):

    organization = models.ForeignKey(Organization, db_index=True)
    name = models.CharField(max_length=64)
    address_1 = models.CharField(max_length=128)
    address_2 = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=64)
    region = models.CharField(max_length=64)
    postal_code = models.CharField(max_length=64)
    country_code = models.CharField(max_length=64)
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    timezone = TimeZoneField()

    class Meta:
        unique_together = ('name', 'organization')


class Location(models.UUIDModel, models.TimestampableModel):

    organization = models.ForeignKey(Organization, db_index=True)
    name = models.CharField(max_length=64)
    address = models.ForeignKey(Address)
    image_url = models.URLField(max_length=255, null=True)

    class Meta:
        unique_together = ('name', 'organization')
        protobuf = organization_containers.LocationV1


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
