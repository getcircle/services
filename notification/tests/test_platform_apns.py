import json

from protobufs.services.notification import containers_pb2 as notification_containers

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import platforms


class TestPlatformAPNS(TestCase):

    def setUp(self):
        super(TestPlatformAPNS, self).setUp()
        self.platform = platforms.APNS(service_token=mocks.mock_token())

    def test_apns_construct_message_group_membership_request_notification(self):
        requester_profile = mocks.mock_profile()
        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=requester_profile.id,
            group_key=fuzzy.FuzzyUUID().fuzz(),
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_containers.NotificationTypeV1.GOOGLE_GROUPS,
            group_membership_request=group_membership_request,
        )
        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=mocks.mock_profile(),
                profile_id=requester_profile.id,
            )
            payload = self.platform.construct_message(
                to_profile_id=fuzzy.FuzzyUUID().fuzz(),
                notification=notification,
            )
        message = json.loads(payload)
        self.assertEqual(message['aps']['alert']['title'], 'Group Membership Request')

    def test_apns_construct_message_group_membership_request_response_notification(self):
        manager_profile = mocks.mock_profile()
        group_membership_request_response = (
            notification_containers.GroupMembershipRequestResponseNotificationV1(
                group_manager_profile_id=manager_profile.id,
                approved=False,
                group_key=fuzzy.FuzzyUUID().fuzz(),
            )
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_containers.NotificationTypeV1.GOOGLE_GROUPS,
            group_membership_request_response=group_membership_request_response,
        )
        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=manager_profile,
                profile_id=manager_profile.id,
            )
            payload = self.platform.construct_message(
                to_profile_id=fuzzy.FuzzyUUID().fuzz(),
                notification=notification,
            )
        message = json.loads(payload)
        self.assertEqual(message['aps']['alert']['title'], 'Group Membership Request Response')
        self.assertIn('denied', message['aps']['alert']['body'])

    def test_apns_construct_message_group_membership_request_response_notification_approved(self):
        manager_profile = mocks.mock_profile()
        group_membership_request_response = (
            notification_containers.GroupMembershipRequestResponseNotificationV1(
                group_manager_profile_id=manager_profile.id,
                approved=True,
                group_key=fuzzy.FuzzyUUID().fuzz(),
            )
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_containers.NotificationTypeV1.GOOGLE_GROUPS,
            group_membership_request_response=group_membership_request_response,
        )
        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=manager_profile,
                profile_id=manager_profile.id,
            )
            payload = self.platform.construct_message(
                to_profile_id=fuzzy.FuzzyUUID().fuzz(),
                notification=notification,
            )
        message = json.loads(payload)
        self.assertEqual(message['aps']['alert']['title'], 'Group Membership Request Response')
        self.assertIn('approved', message['aps']['alert']['body'])
