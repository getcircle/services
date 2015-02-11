from protobufs.user_service_pb2 import UserService

from services.test import (
    factory,
    fuzzy,
)

from . import models


class UserFactory(factory.Factory):
    class Meta:
        model = models.User
        protobuf = UserService.Containers.User

    primary_email = fuzzy.FuzzyText(suffix='@example.com')
    phone_number = factory.Sequence(lambda n: '+1949293%04d' % (n,))

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.set_password(extracted)


class TOTPTokenFactory(factory.Factory):
    class Meta:
        model = models.TOTPToken

    user = factory.SubFactory(UserFactory)
    token = fuzzy.FuzzyText(length=16)


class IdentityFactory(factory.Factory):
    class Meta:
        model = models.Identity
        protobuf = UserService.Containers.Identity

    provider = UserService.LINKEDIN
    user = factory.SubFactory(UserFactory)
    full_name = fuzzy.FuzzyText()
    email = fuzzy.FuzzyText(suffix='@example.com')
    access_token = fuzzy.FuzzyUUID()
    provider_uid = fuzzy.FuzzyUUID()
    expires_at = fuzzy.FuzzyTimestamp()
