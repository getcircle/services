import service.control

from services.test import (
    fuzzy,
    TestCase,
)

from .. import (
    factories,
    models,
)


class TestRequestAccess(TestCase):

    def setUp(self):
        self.client = service.control.Client('user', token='test-token')

    def test_request_access_invalid_user_id(self):
        with self.assertFieldError('user_id'):
            self.client.call_action('request_access', user_id='invalid')

    def test_request_access_user_does_not_exist(self):
        with self.assertFieldError('user_id', 'DOES_NOT_EXIST'):
            self.client.call_action('request_access', user_id=fuzzy.FuzzyUUID().fuzz())

    def test_request_access_missing_arguments(self):
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('request_access')
        self.assertIn('MISSING_ARGUMENTS', expected.exception.response.errors)

    def test_request_access(self):
        user = factories.UserFactory.create_protobuf()
        response = self.client.call_action('request_access', user_id=user.id)
        self.assertEqual(response.result.access_request.user_id, user.id)
        self.assertTrue(models.AccessRequest.objects.filter(user_id=user.id).exists())

    def test_request_access_duplicate_ignored(self):
        user = factories.UserFactory.create_protobuf()
        response = self.client.call_action('request_access', user_id=user.id)
        access_request = response.result.access_request
        response = self.client.call_action('request_access', user_id=user.id)
        self.verify_containers(access_request, response.result.access_request)
