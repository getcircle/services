from mock import patch

from protobufs.services.notification import containers_pb2 as notification_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import factories


class TestRegisterDevice(TestCase):

    def setUp(self):
        super(TestRegisterDevice, self).setUp()
        self.profile = mocks.mock_profile()
        self.client = service.control.Client(
            'notification',
            token=mocks.mock_token(
                profile_id=self.profile.id,
                user_id=self.profile.user_id,
                organization_id=self.profile.organization_id,
            ),
        )

    def test_register_device_device_required(self):
        with self.assertFieldError('device', 'MISSING'):
            self.client.call_action('register_device')

    def test_register_device_device_notification_token_required(self):
        with self.assertFieldError('device.notification_token', 'MISSING'):
            self.client.call_action(
                'register_device',
                device=mocks.mock_device(notification_token=None),
            )

    def test_register_device_device_id_required(self):
        with self.assertFieldError('device.id', 'MISSING'):
            self.client.call_action(
                'register_device',
                device=mocks.mock_device(id=None),
            )

    def test_register_device_apns_already_exists(self):
        device = mocks.mock_device(
            user_id=self.profile.user_id,
            organization_id=self.profile.organization_id,
        )
        token = factories.NotificationTokenFactory.create_protobuf(
            device_id=device.id,
            provider=notification_containers.NotificationTokenV1.SNS,
            provider_platform=notification_containers.NotificationTokenV1.APNS,
            user_id=device.user_id,
            organization_id=device.organization_id,
        )

        response = self.client.call_action('register_device', device=device)
        self.verify_containers(token, response.result.notification_token)

    @patch('notification.providers.sns.boto')
    def test_register_device_apns(self, patched_boto):
        provider_token = fuzzy.FuzzyUUID().fuzz()
        patched_boto.connect_sns().create_platform_endpoint.return_value = (
            {'CreatePlatformEndpointResponse': {
                'CreatePlatformEndpointResult': {'EndpointArn': provider_token}
            }}
        )
        device = mocks.mock_device(user_id=self.profile.user_id)
        response = self.client.call_action(
            'register_device',
            device=device,
        )

        token = response.result.notification_token
        self.assertEqual(token.provider, notification_containers.NotificationTokenV1.SNS)
        self.assertEqual(token.user_id, self.profile.user_id)
        self.assertEqual(token.provider_token, provider_token)
        self.assertEqual(token.device_id, device.id)
