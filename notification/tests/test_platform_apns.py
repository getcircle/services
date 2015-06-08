import json

from protobufs.services.notification import containers_pb2 as notification_containers

from services.test import (
    fuzzy,
    TestCase,
)

from .. import platforms


class TestPlatformAPNS(TestCase):

    def setUp(self):
        super(TestPlatformAPNS, self).setUp()
        self.platform = platforms.APNS()

    def test_apns_construct_message_group_membership_request_notification(self):
        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=fuzzy.FuzzyUUID().fuzz(),
            group_id=fuzzy.FuzzyUUID().fuzz(),
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=(
                notification_containers.NotificationTypeV1.GROUP_MEMBERSHIP_REQUEST
            ),
            group_membership_request=group_membership_request,
        )
        payload = self.platform.construct_message(
            to_profile_id=fuzzy.FuzzyUUID().fuzz(),
            notification=notification,
        )
        message = json.loads(payload)
        self.assertEqual(message['aps']['alert']['title'], 'Group Membership Request')
