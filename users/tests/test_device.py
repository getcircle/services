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
        response = self.client.call_action('record_device', device=device)
        self.verify_containers(device, response.result.device)

        # verify that auth_token was recorded on the device
        self.assertFalse(hasattr(response.result.device, 'last_token'))
        result = models.Device.objects.get(id=response.result.device.id)
        self.assertEqualUUID4(result.last_token, self.parsed_token.auth_token)

        # verify that the auth_token is updated on the device
        token = mocks.mock_token()
        parsed_token = parse_token(token)
        client = service.control.Client('user', token=token)
        client.call_action('record_device', device=device)
        result = models.Device.objects.get(id=response.result.device.id)
        self.assertEqualUUID4(result.last_token, parsed_token.auth_token)

    def test_user_record_multiple_devices(self):
        user = factories.UserFactory.create()
        for _ in range(2):
            device = factories.DeviceFactory.build_protobuf(id=None, user=user)
            response = self.client.call_action('record_device', device=device)
            self.verify_containers(device, response.result.device)

        self.assertEqual(models.Device.objects.filter(user=user).count(), 2)

    def test_user_update_device(self):
        device = factories.DeviceFactory.create_protobuf()
        device.app_version = 'updated'
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
            last_token=factories.TokenFactory.create(user=user).key,
        )
        # create inactive devices
        factories.DeviceFactory.create_batch(
            size=2,
            user=user,
            last_token=fuzzy.FuzzyUUID().fuzz(),
        )

        response = self.client.call_action('get_active_devices', user_id=str(user.id))
        self.assertEqual(len(response.result.devices), len(active_devices))
