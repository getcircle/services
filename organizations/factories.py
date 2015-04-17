from protobufs.services.organization.containers import (
    address_pb2,
    location_pb2,
    organization_pb2,
    team_pb2,
)

from services.test import factory

from . import models


class OrganizationFactory(factory.Factory):
    class Meta:
        model = models.Organization
        protobuf = organization_pb2.OrganizationV1

    name = factory.FuzzyText()
    domain = factory.FuzzyText(suffix='.com')
    image_url = factory.FuzzyText(prefix='http://www.', suffix='.com')


class TeamFactory(factory.Factory):
    class Meta:
        model = models.Team
        protobuf = team_pb2.TeamV1

    name = factory.FuzzyText()
    owner_id = factory.FuzzyUUID()
    path = factory.FuzzyUUID()
    organization = factory.SubFactory(OrganizationFactory)


class AddressFactory(factory.Factory):
    class Meta:
        model = models.Address
        protobuf = address_pb2.AddressV1

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.FuzzyText()
    address_1 = factory.FuzzyText(suffix=' Street')
    address_2 = factory.FuzzyText(suffix=' Suite 700')
    city = factory.FuzzyText()
    region = factory.FuzzyText(length=2)
    postal_code = '94010'
    country_code = 'US'
    latitude = '37.578286'
    longitude = '-122.348729'
    timezone = 'America/Los_Angeles'

    @classmethod
    def get_protobuf_data(cls, **data):
        model = cls.build(**data)
        return model.as_dict(exclude=('created', 'changed'))


class LocationFactory(factory.Factory):
    class Meta:
        model = models.Location
        protobuf = location_pb2.LocationV1

    name = factory.FuzzyText()
    address = factory.SubFactory(AddressFactory)
    organization = factory.SubFactory(OrganizationFactory)

    @classmethod
    def create_protobuf(cls, *args, **kwargs):
        cls.verify_has_protobuf()
        container = cls._meta.protobuf()
        model = cls.create(*args, **kwargs)
        model.to_protobuf(container, address=model.address.as_dict())
        return container
