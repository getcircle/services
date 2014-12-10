import factory

from users.factories import UserFactory

from .models import Credential


class CredentialFactory(factory.DjangoModelFactory):

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Credential
