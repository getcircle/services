import service.control
from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from . import (
    factories,
    models,
)


class AppreciationTests(TestCase):

    def setUp(self):
        super(AppreciationTests, self).setUp()
        self.client = service.control.Client('appreciation', token=mocks.mock_token())

    def test_create_appreciation_invalid_destination_profile_id(self):
        with self.assertFieldError('appreciation.destination_profile_id'):
            self.client.call_action(
                'create_appreciation',
                appreciation={
                    'destination_profile_id': 'invalid',
                    'source_profile_id': fuzzy.FuzzyUUID().fuzz(),
                    'content': 'thanks for nothing!',
                },
            )

    def test_create_appreciation_invalid_source_profile_id(self):
        with self.assertFieldError('appreciation.source_profile_id'):
            self.client.call_action(
                'create_appreciation',
                appreciation={
                    'destination_profile_id': fuzzy.FuzzyUUID().fuzz(),
                    'source_profile_id': 'invalid',
                    'content': 'thanks for nothing!',
                },
            )

    def test_create_appreciation(self):
        expected = {
            'destination_profile_id': fuzzy.FuzzyUUID().fuzz(),
            'source_profile_id': fuzzy.FuzzyUUID().fuzz(),
            'content': 'thanks for everything!',
        }
        response = self.client.call_action('create_appreciation', appreciation=expected)
        self.verify_container_matches_data(response.result.appreciation, expected)

    def test_get_appreciation_invalid_destination_profile_id(self):
        with self.assertFieldError('destination_profile_id'):
            self.client.call_action('get_appreciation', destination_profile_id='invalid')

    def test_get_appreciation_with_destination_profile_id(self):
        destination_profile_id = fuzzy.FuzzyUUID().fuzz()
        expected = factories.AppreciationFactory.create_batch(
            size=3,
            destination_profile_id=destination_profile_id,
        )
        factories.AppreciationFactory.create_batch(size=2)
        most_recent = factories.AppreciationFactory.create_protobuf(
            destination_profile_id=destination_profile_id,
        )
        expected.append(most_recent)

        response = self.client.call_action(
            'get_appreciation',
            destination_profile_id=destination_profile_id,
        )

        # verify we only pulled appreciation for the specified destination_id
        self.assertEqual(len(expected), len(response.result.appreciation))
        for appreciation in response.result.appreciation:
            self.assertEqualUUID4(appreciation.destination_profile_id, destination_profile_id)

        # verify that the most recently created appreciation is first
        self.verify_containers(most_recent, response.result.appreciation[0])

    def test_delete_appreciation_invalid_id(self):
        appreciation = factories.AppreciationFactory.build_protobuf()
        with self.assertFieldError('appreciation.id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_appreciation', appreciation=appreciation)

    def test_delete_appreciation_not_source_or_destination_profile_id(self):
        appreciation = factories.AppreciationFactory.create_protobuf()
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_appreciation', appreciation=appreciation)
        self.assertIn('FORBIDDEN', expected.exception.response.errors)

    def test_delete_appreciation_source_profile_id(self):
        appreciation = factories.AppreciationFactory.create_protobuf()
        self.client.token = mocks.mock_token(profile_id=appreciation.source_profile_id)
        response = self.client.call_action('delete_appreciation', appreciation=appreciation)
        self.assertTrue(response.success)

        appreciation = models.Appreciation.objects.get(pk=appreciation.id)
        self.assertEqual(appreciation.status, models.Appreciation.DELETED_STATUS)

    def test_delete_appreciation_destination_profile_id(self):
        appreciation = factories.AppreciationFactory.create_protobuf()
        self.client.token = mocks.mock_token(profile_id=appreciation.destination_profile_id)
        response = self.client.call_action('delete_appreciation', appreciation=appreciation)
        self.assertTrue(response.success)

        appreciation = models.Appreciation.objects.get(pk=appreciation.id)
        self.assertEqual(appreciation.status, models.Appreciation.DELETED_STATUS)

    def test_update_appreciation_invalid_id(self):
        appreciation = factories.AppreciationFactory.build_protobuf()
        with self.assertFieldError('appreciation.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_appreciation', appreciation=appreciation)

    def test_update_appreciation_not_source_profile_id(self):
        appreciation = factories.AppreciationFactory.create_protobuf()
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_appreciation', appreciation=appreciation)
        self.assertIn('FORBIDDEN', expected.exception.response.errors)

    def test_update_appreciation_destination_profile_id(self):
        appreciation = factories.AppreciationFactory.create_protobuf()
        self.client.token = mocks.mock_token(profile_id=appreciation.destination_profile_id)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_appreciation', appreciation=appreciation)
        self.assertIn('FORBIDDEN', expected.exception.response.errors)

    def test_update_appreciation(self):
        appreciation = factories.AppreciationFactory.create_protobuf()
        new_content = 'new content'
        appreciation.content = new_content
        self.client.token = mocks.mock_token(profile_id=appreciation.source_profile_id)
        response = self.client.call_action('update_appreciation', appreciation=appreciation)
        self.assertEqual(response.result.appreciation.content, new_content)

        appreciation = models.Appreciation.objects.get(pk=appreciation.id)
        self.assertEqual(appreciation.content, new_content)
