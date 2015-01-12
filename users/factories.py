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
    phone_number = factory.Sequence(lambda n: '+1949293%40d' % (n,))


class TOTPTokenFactory(factory.Factory):
    class Meta:
        model = models.TOTPToken

    user = factory.SubFactory(UserFactory)
    token = fuzzy.FuzzyText(length=16)
