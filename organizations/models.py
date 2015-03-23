from common.db import models
from timezone_field import TimeZoneField


class LTreeField(models.Field):

    def db_type(self, connection):
        return 'ltree'


class Organization(models.UUIDModel, models.TimestampableModel):

    name = models.CharField(max_length=64)
    domain = models.CharField(max_length=64, unique=True)
    image_url = models.URLField(max_length=255, null=True)


class Team(models.UUIDModel, models.TimestampableModel):

    protobuf_include_fields = ('department',)

    name = models.CharField(max_length=255)
    owner_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(Organization, db_index=True)
    path = LTreeField(null=True, db_index=True)

    # TODO cache the result
    def get_path(self):
        path_parts = self.path.split('.')
        path = Team.objects.filter(pk__in=path_parts).values(
            'id',
            'name',
            'owner_id',
        )
        # XXX see if we can have the client handle this for us
        for item in path:
            item['id'] = str(item['id'])
            item['owner_id'] = str(item['owner_id'])
        return path

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
