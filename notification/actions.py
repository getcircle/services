from protobufs.services.notification import containers_pb2 as notification_containers
from service import actions

from services import mixins

from . import models


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
