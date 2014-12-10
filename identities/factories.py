import factory

from users.factories import UserFactory


class IdentityFactory(factory.DjangoModelFactory):

    first_name = factory.FuzzyText()
    last_name = factory.FuzzyText()
    email = factory.FuzzyText(suffix='@example.com')
    user = factory.SubFactory(UserFactory)
