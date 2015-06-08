import json

from mock import (
    MagicMock,
    patch,
)
from protobufs.services.notification import containers_pb2 as notification_containers
from protobufs.services.user import containers_pb2 as user_containers

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import providers


class TestProviderSNS(TestCase):

    def setUp(self):
        super(TestProviderSNS, self).setUp()
        self.provider = providers.SNS()

    def test_provider_register_notification_token_unsupported_platform(self):
        with self.assertRaises(providers.exceptions.UnsupportedPlatform):
            self.provider.register_notification_token(
                'fake_token',
                'invalid',
                fuzzy.FuzzyUUID().fuzz(),
            )

    @patch('notification.providers.sns.boto')
    def test_provider_register_notification_token_stores_user_id(self, patched_boto):
        user_id = fuzzy.FuzzyUUID().fuzz()
        self.provider.register_notification_token(
            'fake_token',
            notification_containers.NotificationTokenV1.APNS,
            user_id,
        )

        kwargs = patched_boto.connect_sns().create_platform_endpoint.call_args[1]
        self.assertEqual(json.loads(kwargs['custom_user_data'])['user_id'], user_id)

    def test_provider_get_platform_for_device_device_provider_apple(self):
        platform = self.provider.get_platform_for_device(
            mocks.mock_device(provider=user_containers.DeviceV1.APPLE),
        )
        self.assertEqual(platform, notification_containers.NotificationTokenV1.APNS)

    def test_provider_get_platform_for_device_device_provider_unsupported(self):
        mock_device = MagicMock()
        type(mock_device).provider = 'invalid'
        with self.assertRaises(providers.exceptions.UnsupportedProvider):
            self.provider.get_platform_for_device(mock_device)

    @patch('notification.providers.sns.boto')
    def test_provider_publish_notification(self, patched_boto):
        message = 'message'
        provider_token = 'arn:aws:sns:::endpoint/APNS_SANDBOX/token/'
        self.provider.publish_notification(message, provider_token)
        kwargs = patched_boto.connect_sns().publish.call_args[1]
        self.assertEqual(kwargs['message'], json.dumps({'APNS_SANDBOX': message}))
        self.assertEqual(kwargs['target_arn'], provider_token)
        self.assertEqual(kwargs['message_structure'], 'json')

    def test_provider_get_platform_from_arn(self):
        arn = 'arn:aws:sns:us-east-1:487220619225:endpoint/APNS_SANDBOX/Circle-Dev/asdafdfasdf'
        platform = self.provider._get_platform_from_arn(arn)
        self.assertEqual(platform, 'APNS_SANDBOX')

        arn = 'arn:aws:sns:us-east-1:487220619225:endpoint/APNS/Circle-Dev/asdafdfasdf'
        platform = self.provider._get_platform_from_arn(arn)
        self.assertEqual(platform, 'APNS')
