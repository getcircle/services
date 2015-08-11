import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)
from services.token import parse_token

from .. import (
    factories,
    models,
)


class TestUserDevices(TestCase):

    def setUp(self):
        self.service_token = mocks.mock_token()
        self.parsed_token = parse_token(self.service_token)
        self.client = service.control.Client('user', token=self.service_token)

    def test_record_device_invalid_user_id(self):
        device = factories.DeviceFactory.build_protobuf(id=None)
        device.user_id = 'invalid'
        with self.assertFieldError('device.user_id'):
            self.client.call_action('record_device', device=device)

    def test_record_device_user_does_not_exist(self):
        device = factories.DeviceFactory.build_protobuf(id=None)
        with self.assertFieldError('device.user_id', 'DOES_NOT_EXIST'):
            self.client.call_action('record_device', device=device)

    def test_record_device_required_fields(self):
        device = factories.DeviceFactory.build_protobuf()
        for field, _ in device.ListFields():
            device.ClearField(field.name)

        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('record_device', device=device)

        self.assertIn('FIELD_ERROR', expected.exception.response.errors)
        self.assertEqual(len(expected.exception.response.error_details), 5)

    def test_record_device(self):
        user = factories.UserFactory.create()
        device = factories.DeviceFactory.build_protobuf(id=None, user=user)
        with self.mock_transport() as mock:
            mock.instance.register_empty_response(
                service='notification',
                action='register_device',
                mock_regex_lookup='notification:.*',
            )
            response = self.client.call_action('record_device', device=device)

            self.verify_containers(device, response.result.device)
            # verify that auth_token was recorded on the device
            self.assertFalse(hasattr(response.result.device, 'last_token_id'))
            result = models.Device.objects.get(id=response.result.device.id)
            self.assertEqualUUID4(result.last_token_id, self.parsed_token.auth_token_id)

            # verify that the auth_token is updated on the device
            token = mocks.mock_token()
            parsed_token = parse_token(token)
            self.client.token = token
            self.client.call_action('record_device', device=device)
            result = models.Device.objects.get(id=response.result.device.id)
            self.assertEqualUUID4(result.last_token_id, parsed_token.auth_token_id)

    def test_record_device_no_notification_token_doesnt_register_device(self):
        user = factories.UserFactory.create()
        device = factories.DeviceFactory.build_protobuf(
            id=None,
            user=user,
            notification_token=None,
        )
        response = self.client.call_action('record_device', device=device)
        self.verify_containers(device, response.result.device)

    def test_user_record_multiple_devices(self):
        user = factories.UserFactory.create()
        for _ in range(2):
            device = factories.DeviceFactory.build_protobuf(id=None, user=user)
            with self.mock_transport() as mock:
                mock.instance.register_empty_response(
                    'notification',
                    'register_device',
                    mock_regex_lookup='notification:.*',
                )
                response = self.client.call_action('record_device', device=device)
            self.verify_containers(device, response.result.device)

        self.assertEqual(models.Device.objects.filter(user=user).count(), 2)

    def test_user_update_device(self):
        device = factories.DeviceFactory.create_protobuf()
        device.app_version = 'updated'
        with self.mock_transport() as mock:
            mock.instance.register_empty_response(
                'notification',
                'register_device',
                mock_regex_lookup='notification:.*',
            )
            response = self.client.call_action('record_device', device=device)
        self.verify_containers(device, response.result.device)

        expected = models.Device.objects.get(id=device.id)
        self.assertEqual(device.app_version, expected.app_version)

    def test_user_get_active_devices(self):
        user = factories.UserFactory.create()
        # create active devices
        active_devices = factories.DeviceFactory.create_batch(
            size=2,
            user=user,
            last_token_id=factories.TokenFactory.create(user=user).id,
        )
        # create inactive devices
        factories.DeviceFactory.create_batch(
            size=2,
            user=user,
            last_token_id=fuzzy.FuzzyUUID().fuzz(),
        )

        response = self.client.call_action('get_active_devices', user_id=str(user.id))
        self.assertEqual(len(response.result.devices), len(active_devices))

    def test_user_get_active_devices_no_active_tokens(self):
        user = factories.UserFactory.create()
        factories.DeviceFactory.create_batch(
            size=2,
            user=user,
            last_token_id=fuzzy.FuzzyUUID().fuzz(),
        )

        response = self.client.call_action('get_active_devices', user_id=str(user.id))
        self.assertFalse(response.result.devices)

    def test_user_get_active_devices_user_id_required(self):
        with self.assertFieldError('user_id', 'MISSING'):
            self.client.call_action('get_active_devices')
