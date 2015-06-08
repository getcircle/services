import json

from protobufs.services.notification import containers_pb2 as notification_containers


def group_membership_request_message(to_profile_id, notification, **kwargs):
    # TODO strings should be localized
    # TODO should have some way to validate that the "notification" has all the
    # required fields. Potentially a class that has "validate" and
    # "construct_message"?
    return {
        'aps': {
            'alert': {
                'title': 'Group Membership Request',
                'body': '%s requested to join group %s' % (
                    notification.requester_profile_id,
                    notification.group_id,
                ),
            },
            'sound': 'default',
        },
    }


class Platform(object):

    def construct_message(self, to_profile_id, notification):
        notification_types = notification_containers.NotificationTypeV1
        if notification.notification_type_id == notification_types.GROUP_MEMBERSHIP_REQUEST:
            message = group_membership_request_message(
                to_profile_id,
                notification.group_membership_request,
            )
        return json.dumps(message)
