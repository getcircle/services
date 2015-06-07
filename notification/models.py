from bitfield import BitField
from common.db import models
from common import utils
from protobufs.services.notification import containers_pb2 as notification_containers


class NotificationType(models.TimestampableModel):

    as_dict_value_transforms = {'id': int}

    id = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(
            notification_containers.NotificationTypeV1.TypeV1
        ),
        primary_key=True,
    )
    description = models.CharField(max_length=255)
    channels = BitField(flags=(
        'mobile_push',
    ))
    opt_in = models.BooleanField(default=False)

    class Meta:
        protobuf = notification_containers.NotificationTypeV1


class NotificationPreference(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'notification_type': int}

    profile_id = models.UUIDField()
    notification_type = models.ForeignKey(NotificationType)
    subscribed = models.BooleanField()

    class Meta:
        index_together = ('profile_id', 'notification_type', 'subscribed')
        unique_together = ('profile_id', 'notification_type')
        protobuf = notification_containers.NotificationPreferenceV1


class NotificationToken(models.UUIDModel, models.TimestampableModel):

    as_dict_value_transforms = {'provider': int, 'provider_platform': int}

    user_id = models.UUIDField()
    device_id = models.UUIDField()
    provider_token = models.CharField(max_length=255)
    provider = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(
            notification_containers.NotificationTokenV1.ProviderV1
        ),
    )
    provider_platform = models.SmallIntegerField(
        choices=utils.model_choices_from_protobuf_enum(
            notification_containers.NotificationTokenV1.ProviderPlatformV1
        ),
        null=True,
    )

    class Meta:
        index_together = ('user_id', 'provider')
        protobuf = notification_containers.NotificationTokenV1
