from protobufs.organization_service_pb2 import OrganizationService

from services.test import factory

from . import models


class OrganizationFactory(factory.Factory):
    class Meta:
        model = models.Organization

    name = factory.FuzzyText()
    domain = factory.FuzzyText(suffix='.com')


class TeamFactory(factory.Factory):
    class Meta:
        model = models.Team

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

    @classmethod
    def get_protobuf_data(cls, **data):
        model = cls.build(**data)
        return model.as_dict(exclude=('created', 'changed'))
