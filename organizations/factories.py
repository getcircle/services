from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.organization.containers import integration_pb2

from services.test import factory

from . import models


class OrganizationFactory(factory.Factory):
    class Meta:
        model = models.Organization
        protobuf = organization_containers.OrganizationV1

    name = factory.FuzzyText()
    domain = factory.FuzzyText(suffix='.com')
    image_url = factory.FuzzyText(prefix='http://www.', suffix='.com')


class TeamFactory(factory.Factory):
    class Meta:
        model = models.Team
        protobuf = organization_containers.TeamV1

    name = factory.FuzzyText()
    owner_id = factory.FuzzyUUID()
    path = factory.FuzzyUUID()
    organization = factory.SubFactory(OrganizationFactory)
    description = factory.FuzzyText()


class AddressFactory(factory.Factory):
    class Meta:
        model = models.Address
        protobuf = organization_containers.AddressV1

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
        protobuf = organization_containers.LocationV1

    name = factory.FuzzyText()
    address = factory.SubFactory(AddressFactory)
    organization = factory.SubFactory(OrganizationFactory)
    description = factory.FuzzyText()

    @classmethod
    def create_protobuf(cls, *args, **kwargs):
        cls.verify_has_protobuf()
        container = cls._meta.protobuf()
        model = cls.create(*args, **kwargs)
        model.to_protobuf(container, address=model.address.as_dict())
        return container


class TokenFactory(factory.Factory):
    class Meta:
        model = models.Token
        protobuf = organization_containers.TokenV1

    organization = factory.SubFactory(OrganizationFactory)
    requested_by_user_id = factory.FuzzyUUID()


class IntegrationFactory(factory.Factory):
    class Meta:
        model = models.Integration
        protobuf = integration_pb2.IntegrationV1

    organization = factory.SubFactory(OrganizationFactory)
    type = integration_pb2.GOOGLE_GROUPS
