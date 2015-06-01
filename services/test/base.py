from contextlib import contextmanager
import uuid
from django.test import TestCase as DjangoTestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView
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

    def tearDown(self):
        super(TestCase, self).tearDown()
        mock.instance.clear()

    @contextmanager
    def assertFieldError(self, key, detail='INVALID'):
        with self.assertRaisesCallActionError() as expected:
            yield
        self._verify_error(expected.exception.response, 'FIELD_ERROR', key, detail)

    @contextmanager
    def assertRaisesCallActionError(self):
        with self.assertRaises(service.control.CallActionError) as expected:
            yield expected

    def _verify_values(self, expected_value, value, message=''):
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
        self.assertEqual(
            value,
            expected_value,
            '%s - expected: "%s", got: "%s"' % (message, expected_value, value),
        )

    def verify_container_matches_data(self, container, data):
        for key, value in data.iteritems():
            self._verify_values(value, getattr(container, key), message='key: %s' % (key,))

    def verify_containers(self, expected, to_verify):
        for field, expected_value in expected.ListFields():
            value = getattr(to_verify, field.name, None)
            self._verify_values(expected_value, value, message='field: %s' % (field.name,))

    def assertEqualUUID4(self, first, second):
        try:
            self.assertTrue(matching_uuids(first, second))
        except AssertionError:
            raise AssertionError('%s does not equal %s' % (first, second))

    def assertNotEqualUUID4(self, first, second):
        try:
            self.assertFalse(matching_uuids(first, second))
        except AssertionError:
            raise AssertionError('%s equals %s' % (first, second))

    @contextmanager
    def mock_transport(self, client=None):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        if client:
            client.set_transport(local.instance)
        yield mock
        service.settings.DEFAULT_TRANSPORT = 'service.transports.local.instance'


class TestAuthView(APIView):

    def get(self, request, *args, **kwargs):
        if not request.auth:
            raise AuthenticationFailed()
        return Response(status=HTTP_200_OK)
