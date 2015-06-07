from protobufs.services.notification import containers_pb2 as notification_containers
from service import actions

from services import mixins

from . import (
    models,
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
                notification_token=self.request.device.notification_token,
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
