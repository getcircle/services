from contextlib import contextmanager
import uuid
from django.test import TestCase as DjangoTestCase
import service.control
from service.transports import (
    local,
    mock,
)

from ..utils import matching_uuids


class TestCase(DjangoTestCase):

    def _verify_error(self, response, code, key, detail):
        self.assertFalse(response.success)
        self.assertIn(code, response.errors)
        error = response.error_details[0]
        self.assertEqual(key, error.key)
        self.assertEqual(detail, error.detail)

    @contextmanager
    def assertFieldError(self, key, detail='INVALID'):
        with self.assertRaisesCallActionError() as expected:
            yield
        self._verify_error(expected.exception.response, 'FIELD_ERROR', key, detail)

    @contextmanager
    def assertRaisesCallActionError(self):
        with self.assertRaises(service.control.Client.CallActionError) as expected:
            yield expected

    def _verify_values(self, expected_value, value):
        uuid_convertibles = (basestring, uuid.UUID)
        if isinstance(value, uuid_convertibles) or isinstance(expected_value, uuid_convertibles):
            # handle various types of UUID (hex and string)
            try:
                if isinstance(value, basestring):
                    value = uuid.UUID(value, version=4)
                if isinstance(expected_value, basestring):
                    expected_value = uuid.UUID(expected_value, version=4)
            except ValueError:
                pass
        self.assertEqual(value, expected_value)

    def _verify_container_matches_data(self, container, data):
        for key, value in data.iteritems():
            self._verify_values(getattr(container, key), value)

    def _verify_containers(self, expected, to_verify):
        for field, expected_value in expected.ListFields():
            value = getattr(to_verify, field.name, None)
            self._verify_values(expected_value, value)

    def assertEqualUUID4(self, first, second):
        self.assertTrue(matching_uuids(first, second))

    @contextmanager
    def default_mock_transport(self, client):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        client.set_transport(local.instance)
        yield mock
        service.settings.DEFAULT_TRANSPORT = 'service.transports.local.instance'
