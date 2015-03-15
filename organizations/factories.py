from protobufs.organization_service_pb2 import OrganizationService

from services.test import factory

from . import models


class OrganizationFactory(factory.Factory):
    class Meta:
        model = models.Organization
        protobuf = OrganizationService.Containers.Organization

    name = factory.FuzzyText()
    domain = factory.FuzzyText(suffix='.com')
    image_url = factory.FuzzyText(prefix='http://www.', suffix='.com')


class TeamFactory(factory.Factory):
    class Meta:
        model = models.Team
        protobuf = OrganizationService.Containers.Team

    name = factory.FuzzyText()
    owner_id = factory.FuzzyUUID()
    path = factory.FuzzyUUID()
    organization = factory.SubFactory(OrganizationFactory)


class AddressFactory(factory.Factory):
    class Meta:
        model = models.Address
        protobuf = OrganizationService.Containers.Address

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
        protobuf = OrganizationService.Containers.Location

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
