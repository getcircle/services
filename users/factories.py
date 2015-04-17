from protobufs.services.user.containers import (
    user_pb2,
    identity_pb2,
    device_pb2,
)


from services.test import (
    factory,
    fuzzy,
)

from . import models


class UserFactory(factory.Factory):
    class Meta:
        model = models.User
        protobuf = user_pb2.UserV1

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
        protobuf = identity_pb2.IdentityV1

    provider = identity_pb2.IdentityV1.LINKEDIN
    user = factory.SubFactory(UserFactory)
    full_name = fuzzy.FuzzyText()
    email = fuzzy.FuzzyText(suffix='@example.com')
    access_token = fuzzy.FuzzyUUID()
    provider_uid = fuzzy.FuzzyUUID()
    expires_at = fuzzy.FuzzyTimestamp()


class DeviceFactory(factory.Factory):
    class Meta:
        model = models.Device
        protobuf = device_pb2.DeviceV1

    user = factory.SubFactory(UserFactory)
    notification_token = fuzzy.FuzzyUUID()
    platform = fuzzy.FuzzyText()
    os_version = fuzzy.FuzzyText()
    app_version = fuzzy.FuzzyText()
    device_uuid = fuzzy.FuzzyUUID()
    language_preference = 'en'
