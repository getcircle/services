from mock import patch
from protobufs.services.notification import containers_pb2 as notification_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import (
    factories,
    models,
)


class TestSendNotification(TestCase):

    def setUp(self):
        super(TestSendNotification, self).setUp()
        self.profile = mocks.mock_profile()
        self.organization = mocks.mock_organization()
        self.client = service.control.Client(
            'notification',
            token=mocks.mock_token(
                profile_id=self.profile.id,
                organization_id=self.organization.id,
            ),
        )

    def test_send_notification_notification_required(self):
        with self.assertFieldError('notification', 'MISSING'):
            self.client.call_action('send_notification', to_profile_id=self.profile.id)

    def test_send_notification_notification_type_required(self):
        with self.assertFieldError('notification.notification_type_id', 'MISSING'):
            self.client.call_action(
                'send_notification',
                to_profile_id=self.profile.id,
                notification={'group_membership_request': {'group_id': fuzzy.FuzzyUUID().fuzz()}},
            )

    def test_send_notification_recipients_required(self):
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'send_notification',
                notification={
                    'notification_type_id': (
                        notification_containers.NotificationTypeV1.GOOGLE_GROUPS
                    ),
                },
            )

        self.assertIn('MISSING_RECIPIENTS', expected.exception.response.errors)

    def test_send_notification_group_membership_request_not_opted_in(self):
        models.NotificationType.objects.all().update(opt_in=True)
        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=fuzzy.FuzzyUUID().fuzz(),
            group_id=fuzzy.FuzzyUUID().fuzz(),
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_containers.NotificationTypeV1.GOOGLE_GROUPS,
            group_membership_request=group_membership_request,
        )
        with self.assertFieldError('notification.notification_type_id', 'NOT_OPTED_IN'):
            self.client.call_action(
                'send_notification',
                to_profile_id=fuzzy.FuzzyUUID().fuzz(),
                notification=notification,
            )

    def test_send_notification_group_membership_request_explicit_opt_out(self):
        profile_id = fuzzy.FuzzyUUID().fuzz()
        models.NotificationType.objects.all().update(opt_in=True)
        notification_type = models.NotificationType.objects.all()[0]

        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=fuzzy.FuzzyUUID().fuzz(),
            group_id=fuzzy.FuzzyUUID().fuzz(),
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_type.id,
            group_membership_request=group_membership_request,
        )
        factories.NotificationPreferenceFactory.create(
            notification_type=notification_type,
            profile_id=profile_id,
            organization_id=self.organization.id,
            subscribed=False,
        )

        with self.assertFieldError('notification.notification_type_id', 'UNSUBSCRIBED'):
            self.client.call_action(
                'send_notification',
                to_profile_id=profile_id,
                notification=notification,
            )

    def test_send_notification_group_membership_request_default_in_opted_out(self):
        profile_id = fuzzy.FuzzyUUID().fuzz()
        models.NotificationType.objects.all().update(opt_in=False)
        notification_type = models.NotificationType.objects.all()[0]

        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=fuzzy.FuzzyUUID().fuzz(),
            group_id=fuzzy.FuzzyUUID().fuzz(),
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_type.id,
            group_membership_request=group_membership_request,
        )
        factories.NotificationPreferenceFactory.create(
            notification_type=notification_type,
            organization_id=self.organization.id,
            profile_id=profile_id,
            subscribed=False,
        )

        with self.assertFieldError('notification.notification_type_id', 'UNSUBSCRIBED'):
            self.client.call_action(
                'send_notification',
                to_profile_id=profile_id,
                notification=notification,
            )

    @patch('notification.actions.providers.sns.boto')
    def test_send_notification_group_membership_request(self, patched_boto):
        to_profile = mocks.mock_profile()
        requester_profile = mocks.mock_profile()

        models.NotificationType.objects.all().update(opt_in=False)
        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=requester_profile.id,
            group_id=fuzzy.FuzzyUUID().fuzz(),
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_containers.NotificationTypeV1.GOOGLE_GROUPS,
            group_membership_request=group_membership_request,
        )

        device = mocks.mock_device(user_id=to_profile.user_id)
        token = factories.NotificationTokenFactory.create(
            user_id=to_profile.user_id,
            device_id=device.id,
            provider_platform=notification_containers.NotificationTokenV1.APNS,
        )

        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=to_profile,
                profile_id=to_profile.id,
            )
            mock.instance.register_empty_response(
                service='group',
                action='get_group',
                group_id=group_membership_request.group_id,
                provider=group_membership_request.provider,
            )
            mock.instance.register_mock_object(
                service='user',
                action='get_active_devices',
                return_object_path='devices',
                return_object=[device],
                user_id=to_profile.user_id,
            )
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=requester_profile,
                profile_id=requester_profile.id,
            )
            self.client.call_action(
                'send_notification',
                to_profile_id=to_profile.id,
                notification=notification,
            )

        kwargs = patched_boto.connect_sns().publish.call_args[1]
        self.assertEqual(kwargs['target_arn'], token.provider_token)

    def test_send_notification_no_active_devices(self):
        to_profile = mocks.mock_profile()

        models.NotificationType.objects.all().update(opt_in=False)
        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=fuzzy.FuzzyUUID().fuzz(),
            group_id=fuzzy.FuzzyUUID().fuzz(),
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
                return_object=to_profile,
                profile_id=to_profile.id,
            )
            mock.instance.register_mock_object(
                service='user',
                action='get_active_devices',
                return_object_path='devices',
                return_object=[],
                user_id=to_profile.user_id,
            )
            with self.assertFieldError('to_profile_id', 'NO_ACTIVE_DEVICES'):
                self.client.call_action(
                    'send_notification',
                    to_profile_id=to_profile.id,
                    notification=notification,
                )

    def test_send_notification_no_notification_tokens(self):
        to_profile = mocks.mock_profile()

        models.NotificationType.objects.all().update(opt_in=False)
        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=fuzzy.FuzzyUUID().fuzz(),
            group_id=fuzzy.FuzzyUUID().fuzz(),
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_containers.NotificationTypeV1.GOOGLE_GROUPS,
            group_membership_request=group_membership_request,
        )

        device = mocks.mock_device(user_id=to_profile.user_id)
        with self.mock_transport() as mock:
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=to_profile,
                profile_id=to_profile.id,
            )
            mock.instance.register_mock_object(
                service='user',
                action='get_active_devices',
                return_object_path='devices',
                return_object=[device],
                user_id=to_profile.user_id,
            )
            with self.assertFieldError('to_profile_id', 'NO_NOTIFICATION_TOKENS'):
                self.client.call_action(
                    'send_notification',
                    to_profile_id=to_profile.id,
                    notification=notification,
                )

    @patch('notification.actions.providers.sns.boto')
    def test_send_notification_group_membership_request_to_profile_ids(self, patched_boto):
        to_profiles = [mocks.mock_profile(), mocks.mock_profile()]
        requester_profile = mocks.mock_profile()

        models.NotificationType.objects.all().update(opt_in=False)
        group_membership_request = notification_containers.GroupMembershipRequestNotificationV1(
            requester_profile_id=requester_profile.id,
            group_id=fuzzy.FuzzyUUID().fuzz(),
        )
        notification = notification_containers.NotificationV1(
            notification_type_id=notification_containers.NotificationTypeV1.GOOGLE_GROUPS,
            group_membership_request=group_membership_request,
        )

        device_map = {}
        for profile in to_profiles:
            device = mocks.mock_device(user_id=profile.user_id)
            factories.NotificationTokenFactory.create(
                user_id=profile.user_id,
                device_id=device.id,
                provider_platform=notification_containers.NotificationTokenV1.APNS,
            )
            device_map[profile.id] = device

        with self.mock_transport() as mock:
            for profile in to_profiles:
                mock.instance.register_mock_object(
                    service='profile',
                    action='get_profile',
                    return_object_path='profile',
                    return_object=profile,
                    profile_id=profile.id,
                )
                mock.instance.register_mock_object(
                    service='user',
                    action='get_active_devices',
                    return_object_path='devices',
                    return_object=[device_map[profile.id]],
                    user_id=profile.user_id,
                )

            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=requester_profile,
                profile_id=requester_profile.id,
            )
            mock.instance.register_empty_response(
                service='group',
                action='get_group',
                group_id=group_membership_request.group_id,
                provider=group_membership_request.provider,
            )

            self.client.call_action(
                'send_notification',
                to_profile_ids=[profile.id for profile in to_profiles],
                notification=notification,
            )

        self.assertEqual(patched_boto.connect_sns().publish.call_count, 2)
        kwargs = patched_boto.connect_sns().publish.call_args[1]
        self.assertIn('target_arn', kwargs)
