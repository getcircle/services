import factory
from services.test import fuzzy

from . import models


class OrganizationFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Organization

    name = fuzzy.FuzzyText()
    domain = fuzzy.FuzzyText(suffix='.com')


class TeamFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Team

    name = fuzzy.FuzzyText()
    owner_id = fuzzy.FuzzyUUID()
    path = fuzzy.FuzzyUUID()
    organization = factory.SubFactory(OrganizationFactory)


class AddressFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Address

    organization = factory.SubFactory(OrganizationFactory)
    name = fuzzy.FuzzyText()
    address_1 = fuzzy.FuzzyText(suffix=' Street')
    address_2 = fuzzy.FuzzyText(suffix=' Suite 700')
    city = fuzzy.FuzzyText()
    region = fuzzy.FuzzyText(length=2)
    postal_code = '94010'
    country_code = 'US'

    @classmethod
    def get_protobuf_data(cls, **data):
        model = cls.build(**data)
        return model.as_dict(exclude=('created', 'changed'))
