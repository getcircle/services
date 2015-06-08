import json

from protobufs.services.notification import containers_pb2 as notification_containers
import service.control


class Platform(object):

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

    def construct_message(self, to_profile_id, notification):
        notification_types = notification_containers.NotificationTypeV1
        if notification.notification_type_id == notification_types.GOOGLE_GROUPS:
            if notification.HasField('group_membership_request'):
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

    def group_membership_request_message(self, to_profile_id, notification, **kwargs):
        profile = self._get_profile(notification.requester_profile_id)
        # TODO strings should be localized
        # TODO should have some way to validate that the "notification" has all the
        # required fields. Potentially a class that has "validate" and
        # "construct_message"?
        return {
            'aps': {
                'alert': {
                    'title': 'Group Membership Request',
                    'body': '%s requested to join group %s' % (
                        ' '.join([profile.first_name, profile.last_name]).strip(),
                        notification.group_key,
                    ),
                },
                'sound': 'default',
            },
        }

    def group_membership_request_response_message(self, to_profile_id, notification, **kwargs):
        profile = self._get_profile(notification.group_manager_profile_id)
        if notification.approved:
            action = 'approved'
        else:
            action = 'denied'
        return {
            'aps': {
                'alert': {
                    'title': 'Group Membership Request Response',
                    'body': '%s %s your request to join %s' % (
                        ' '.join([profile.first_name, profile.last_name]).strip(),
                        action,
                        notification.group_key,
                    ),
                },
                'sound': 'default',
            },
        }
