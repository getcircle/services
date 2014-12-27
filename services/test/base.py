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
