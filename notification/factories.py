from protobufs.services.notification import containers_pb2 as notification_containers

from services.test import factory

from . import models


class NotificationTypeFactory(factory.Factory):
    class Meta:
        model = models.NotificationType
        protobuf = notification_containers.NotificationTypeV1

    id = notification_containers.NotificationTypeV1.GROUP_MEMBERSHIP_REQUEST
    description = factory.FuzzyText()


class NotificationPreferenceFactory(factory.Factory):
    class Meta:
        model = models.NotificationPreference
        protobuf = notification_containers.NotificationPreferenceV1

    subscribed = True


class NotificationTokenFactory(factory.Factory):
    class Meta:
        model = models.NotificationToken
        protobuf = notification_containers.NotificationTokenV1

    user_id = factory.FuzzyUUID()
    device_id = factory.FuzzyUUID()
    provider_token = factory.FuzzyUUID()
    provider = notification_containers.NotificationTokenV1.SNS