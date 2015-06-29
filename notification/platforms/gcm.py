from .base import BasePlatform


class Platform(BasePlatform):

    def group_membership_request_message(self, to_profile_id, notification, **kwargs):
        profile = self._get_profile(notification.requester_profile_id)
        group = self._get_group(notification.group_id, notification.provider)
        # TODO strings should be localized
        # TODO should have some way to validate that the "notification" has all the
        # required fields. Potentially a class that has "validate" and
        # "construct_message"?
        return {
            'GCM': {
                'data': {
                    'title': 'Group Membership Request',
                    'body': '%s requested to join group %s' % (
                        ' '.join([profile.first_name, profile.last_name]).strip(),
                        self._get_group_display_name(group),
                    ),
                    'request_id': notification.request_id,
                },
            },
        }

    def group_membership_request_response_message(self, to_profile_id, notification, **kwargs):
        profile = self._get_profile(notification.group_manager_profile_id)
        group = self._get_group(notification.group_id, notification.provider)
        if notification.approved:
            action = 'approved'
        else:
            action = 'denied'
        return {
            'GCM': {
                'data': {
                    'title': 'Group Membership Request Response',
                    'body': '%s %s your request to join %s' % (
                        ' '.join([profile.first_name, profile.last_name]).strip(),
                        action,
                        self._get_group_display_name(group),
                    ),
                },
            },
        }
