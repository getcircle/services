from django.conf import settings
import mock
from rest_framework import status
from rest_framework.test import APIClient

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from hooks.email import actions
from hooks.helpers import get_root_url
from hooks.tasks import create_post_from_message
from .helpers import (
    return_contents,
    return_fixture,
)


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.api = APIClient()
        self.organization = mocks.mock_organization(domain='example')
        self.profile = mocks.mock_profile(
            organization_id=self.organization.id,
            email='example@example.com',
        )

    def _mock_profile_exists(self, profile=None, organization=None):
        if not profile:
            profile = self.profile

        if not organization:
            organization = self.organization

        mock_response = self.mock.get_mockable_response('profile', 'profile_exists')
        mock_response.exists = True
        mock_response.profile_id = profile.id
        mock_response.user_id = profile.user_id
        mock_response.organization_id = organization.id
        self.mock.instance.register_mock_response(
            service='profile',
            action='profile_exists',
            mock_response=mock_response,
            domain=organization.domain,
            email=profile.email,
        )

    def _mock_mark_message_as_processed(self, patched_boto):
        patched_boto.client().copy_object.side_effect = (
            lambda *args, **kwargs: {'CopyObjectResult': {}}
        )
        patched_boto.client().delete_object.side_effect = (
            lambda *args, **kwargs: {'ResponseMetadata': {'HTTPStatusCode': 204}}
        )

    def test_get_profile_for_source_does_not_exist(self):
        source_details = actions.get_details_for_source('example', 'nothere@example.com')
        self.assertIsNone(source_details)

    def test_get_profile_for_source(self):
        self._mock_profile_exists()
        source_details = actions.get_details_for_source(
            self.organization.domain,
            self.profile.email,
        )
        self.assertEqual(source_details.profile_id, self.profile.id)
        self.assertEqual(source_details.organization_id, self.organization.id)

    def test_perform_authentication_token_required(self):
        response = self.api.post('/hooks/email/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_perform_authentication_invalid_token(self):
        response = self.api.post('/hooks/email/', {'token': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_perform_authentication_source_missing(self):
        response = self.api.post('/hooks/email/', {'token': settings.EMAIL_HOOK_SECRET_KEYS[0]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_perform_authentication_organization_doesnt_exist(self):
        response = self.api.post(
            '/hooks/email/',
            {
                'token': settings.EMAIL_HOOK_SECRET_KEYS[0],
                'source': 'example@example.com',
                'recipients': ['create@example.lunohq.com'],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_perform_authentication_profile_doesnt_exist(self):
        organization = mocks.mock_organization()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object=organization,
            return_object_path='organization',
            domain=organization.domain,
        )
        response = self.api.post(
            '/hooks/email/',
            {
                'token': settings.EMAIL_HOOK_SECRET_KEYS[0],
                'source': 'example@%s.com' % (organization.domain,),
                'recipients': ['create@example.lunohq.com'],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_extract_domain_from_endpoint(self):
        domain = actions.extract_domain('michael@example.com', 'create@company.lunohq.com')
        self.assertEqual(domain, 'company')
        domain = actions.extract_domain('michael@test.com', 'create@company.dev.lunohq.com')
        self.assertEqual(domain, 'company')

    def test_extract_domain_from_source(self):
        domain = actions.extract_domain('michael@example.com', 'create@mail.lunohq.com')
        self.assertEqual(domain, 'example')
        domain = actions.extract_domain('michael@example.com', 'create@mail.dev.lunohq.com')
        self.assertEqual(domain, 'example')

    def test_process_notification_message_id_not_present(self):
        self._mock_profile_exists()
        response = self.api.post(
            '/hooks/email/',
            {
                'token': settings.EMAIL_HOOK_SECRET_KEYS[0],
                'source': 'example@%s.com' % (self.organization.domain,),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('hooks.email.actions.boto3')
    def test_process_notification_multipart(self, patched_boto):
        self._mock_profile_exists()
        self._mock_mark_message_as_processed(patched_boto)
        return_fixture('multipart_email.txt', patched_boto)
        response = self.api.post(
            '/hooks/email/',
            {
                'token': settings.EMAIL_HOOK_SECRET_KEYS[0],
                'source': 'example@%s.com' % (self.organization.domain,),
                'recipients': ['create@example.lunohq.com'],
                'message_id': fuzzy.uuid(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch('hooks.email.actions.boto3')
    def test_create_post_from_message_empty_contents(self, patched_boto):
        return_contents('', patched_boto)
        with self.assertRaises(ValueError):
            create_post_from_message(
                'invalid id',
                fuzzy.uuid(),
                fuzzy.uuid(),
                fuzzy.text(),
                fuzzy.text(),
            )

    @mock.patch('hooks.email.actions.boto3')
    def test_mark_message_as_processed(self, patched_boto):
        message_id = fuzzy.uuid()
        self._mock_mark_message_as_processed(patched_boto)

        actions.mark_message_as_processed(message_id)
        self.assertEqual(patched_boto.client().copy_object.call_count, 1)
        call_kwargs = patched_boto.client().copy_object.call_args[1]
        self.assertEqual(
            call_kwargs['CopySource'],
            'dev-lunohq-emails/local-unprocessed/%s' % (message_id,),
        )
        self.assertEqual(call_kwargs['Key'], 'local-processed/%s' % (message_id,))
        self.assertEqual(call_kwargs['Bucket'], 'dev-lunohq-emails')

        self.assertEqual(patched_boto.client().delete_object.call_count, 1)
        call_kwargs = patched_boto.client().delete_object.call_args[1]
        self.assertEqual(call_kwargs['Bucket'], 'dev-lunohq-emails')
        self.assertEqual(call_kwargs['Key'], 'local-unprocessed/%s' % (message_id,))

    @mock.patch('hooks.email.actions.boto3')
    def test_create_post_from_message(self, patched_boto):
        self._mock_mark_message_as_processed(patched_boto)
        return_fixture('simple_email.txt', patched_boto)
        create_post_from_message(
            fuzzy.uuid(),
            fuzzy.uuid(),
            fuzzy.uuid(),
            fuzzy.text(),
            fuzzy.text(),
        )
        self.assertEqual(patched_boto.client().copy_object.call_count, 1)
        self.assertEqual(patched_boto.client().send_email.call_count, 1)

    @mock.patch('hooks.email.actions.boto3')
    def test_create_post_from_message_multipart(self, patched_boto):
        self._mock_mark_message_as_processed(patched_boto)
        return_fixture('multipart_email.txt', patched_boto)
        create_post_from_message(
            fuzzy.uuid(),
            fuzzy.uuid(),
            fuzzy.uuid(),
            fuzzy.text(),
            fuzzy.text(),
        )
        self.assertEqual(patched_boto.client().copy_object.call_count, 1)
        self.assertEqual(patched_boto.client().send_email.call_count, 1)

    @mock.patch('hooks.email.actions.boto3')
    def test_send_confirmation_to_user(self, patched_boto):
        post = mocks.mock_post()
        email = 'test@example.com'
        actions.send_confirmation_to_user(post, email, 'example')
        call_kwargs = patched_boto.client().send_email.call_args[1]
        self.assertEqual(call_kwargs['Source'], '"Luno"<notifications@lunohq.com>')
        self.assertEqual(call_kwargs['Destination']['ToAddresses'][0], email)
        self.assertIn(post.title, call_kwargs['Message']['Subject']['Data'])
        body = call_kwargs['Message']['Body']['Text']['Data']
        self.assertIn(post.title, body)
        root_url = get_root_url(self.organization.domain)
        self.assertIn(
            ' %s ' % (root_url,),
            body,
            'Root URL should be a stand alone link within the body',
        )
