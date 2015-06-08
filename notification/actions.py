from protobufs.services.notification import containers_pb2 as notification_containers
from service import actions
import service.control

from services import mixins

from . import (
    models,
    platforms,
    providers,
)


class GetPreferences(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = ('channel',)

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.channel == notification_containers.MOBILE_PUSH:
            parameters = {'channels': models.NotificationType.channels.mobile_push}

        notification_types = models.NotificationType.objects.filter(**parameters)
        preferences = models.NotificationPreference.objects.filter(
            profile_id=self.parsed_token.profile_id,
        )
        notification_type_to_preference = dict((preference.notification_type_id, preference) for
                                               preference in preferences)
        # TODO paginate this
        for notification_type in notification_types:
            preference = notification_type_to_preference.get(notification_type.id)
            container = notification_type.to_protobuf()

            subscribed = not container.opt_in
            if preference:
                subscribed = preference.subscribed

            self.response.preferences.add(
                profile_id=self.parsed_token.profile_id,
                notification_type_id=container.id,
                subscribed=subscribed,
                notification_type=container,
            )


class UpdatePreference(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'preference',
        'preference.notification_type_id',
        'preference.subscribed',
    )

    def run(self, *args, **kwargs):
        if not self.request.preference.id:
            preference = models.NotificationPreference.objects.from_protobuf(
                self.request.preference,
                profile_id=self.parsed_token.profile_id,
            )
        else:
            try:
                preference = models.NotificationPreference.objects.get(
                    pk=self.request.preference.id,
                )
            except models.NotificationPreference.DoesNotExist:
                raise self.ActionFieldError('preference.id', 'DOES_NOT_EXIST')

            preference.update_from_protobuf(self.request.preference)
            preference.save()

        preference.to_protobuf(self.response.preference)


class RegisterDevice(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'device',
        'device.id',
        'device.notification_token',
        'device.provider',
    )

    def run(self, *args, **kwargs):
        provider = providers.SNS()
        provider_platform = provider.get_platform_for_device(self.request.device)
        try:
            notification_token = models.NotificationToken.objects.get(
                device_id=self.request.device.id,
                user_id=self.parsed_token.user_id,
                provider=provider.provider,
                provider_platform=provider_platform,
            )
        except models.NotificationToken.DoesNotExist:
            provider_token = provider.register_notification_token(
                token=self.request.device.notification_token,
                platform=provider_platform,
                user_id=self.parsed_token.user_id,
            )
            notification_token = models.NotificationToken.objects.create(
                user_id=self.parsed_token.user_id,
                device_id=self.request.device.id,
                provider_token=provider_token,
                provider=provider.provider,
                provider_platform=provider_platform,
            )

        notification_token.to_protobuf(self.response.notification_token)


class SendNotification(actions.Action):

    required_fields = (
        'notification',
        'notification.notification_type_id',
    )

    def validate(self, *args, **kwargs):
        super(SendNotification, self).validate(*args, **kwargs)
        if not self.is_error():
            if not any([self.request.HasField('to_profile_id'), self.request.to_profile_ids]):
                raise self.ActionError(
                    'MISSING_RECIPIENTS',
                    (
                        'MISSING_RECIPIENTS',
                        'must specify one of ("to_profile_id", "to_profile_ids"',
                    ),
                )

    def _send_notification(self, to_profile_id, notification_type, notification_preference):
        if notification_type.opt_in and not notification_preference:
            raise self.ActionFieldError('notification.notification_type_id', 'NOT_OPTED_IN')
        elif notification_preference and not notification_preference.subscribed:
            raise self.ActionFieldError('notification.notification_type_id', 'UNSUBSCRIBED')

        profile = service.control.get_object(
            service='profile',
            action='get_profile',
            return_object='profile',
            client_kwargs={'token': self.token},
            profile_id=to_profile_id,
        )
        devices = service.control.get_object(
            service='user',
            action='get_active_devices',
            return_object='devices',
            client_kwargs={'token': self.token},
            user_id=profile.user_id,
        )

        # XXX should support indexing these properly
        if not devices:
            raise self.ActionFieldError('to_profile_id', 'NO_ACTIVE_DEVICES')

        notification_tokens = models.NotificationToken.objects.filter(
            user_id=profile.user_id,
            device_id__in=[device.id for device in devices],
        )

        if not notification_tokens:
            raise self.ActionFieldError('to_profile_id', 'NO_NOTIFICATION_TOKENS')

        for notification_token in notification_tokens:
            provider = providers.SNS()
            provider_platform = notification_token.provider_platform
            if provider_platform == notification_containers.NotificationTokenV1.APNS:
                platform = platforms.APNS()
                message = platform.construct_message(
                    to_profile_id,
                    self.request.notification,
                )
                provider.publish_notification(message, notification_token.provider_token)

    def run(self, *args, **kwargs):
        if self.request.to_profile_id:
            to_profile_ids = [self.request.to_profile_id]
        else:
            to_profile_ids = self.request.to_profile_ids

        notification_type = models.NotificationType.objects.get(
            pk=self.request.notification.notification_type_id,
        )
        preferences = models.NotificationPreference.objects.filter(
            profile_id__in=to_profile_ids,
            notification_type=notification_type,
        )
        preferences_dict = dict(
            (preference.profile_id.hex, preference) for preference in preferences
        )
        for to_profile_id in to_profile_ids:
            self._send_notification(
                to_profile_id,
                notification_type,
                preferences_dict.get(to_profile_id),
            )
