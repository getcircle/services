import uuid
from django.test import TestCase as DjangoTestCase


class TestCase(DjangoTestCase):

    def _verify_error(self, response, code, key, detail):
        self.assertFalse(response.success)
        self.assertIn(code, response.errors)
        error = response.error_details[0]
        self.assertEqual(key, error.key)
        self.assertEqual(detail, error.detail)

    def _verify_field_error(self, response, key, detail='INVALID'):
        self._verify_error(response, 'FIELD_ERROR', key, detail)

    def _verify_containers(self, expected, to_verify):
        for field, expected_value in expected.ListFields():
            value = getattr(to_verify, field.name, None)
            if isinstance(value, basestring):
                # handle various types of UUID (hex and string)
                try:
                    value = uuid.UUID(value, version=4)
                    expected_value = uuid.UUID(expected_value, version=4)
                except ValueError:
                    pass
            self.assertEqual(value, expected_value)
