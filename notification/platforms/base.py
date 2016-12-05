import json

import service.control
from protobufs.services.notification import containers_pb2 as notification_containers


class BasePlatform(object):

    def __init__(self, service_token):
        self.token = service_token

    def _get_profile(self, profile_id):
        return service.control.get_object(
            service='profile',
            action='get_profile',
            client_kwargs={'token': self.token},
            return_object='profile',
            profile_id=profile_id,
        )

    def _get_group(self, group_id, provider):
        return service.control.get_object(
            service='group',
            action='get_group',
            client_kwargs={'token': self.token},
            return_object='group',
            group_id=group_id,
            provider=provider,
        )

    def _get_group_display_name(self, group):
        return group.display_name or group.name

    def construct_message(self, to_profile_id, notification):
        notification_types = notification_containers.NotificationTypeV1
        if notification.notification_type_id == notification_types.GOOGLE_GROUPS:
            if notification.group_membership_request.ByteSize():
                message = self.group_membership_request_message(
                    to_profile_id,
                    notification.group_membership_request,
                )
            else:
                message = self.group_membership_request_response_message(
                    to_profile_id,
                    notification.group_membership_request_response,
                )
        return json.dumps(message)
