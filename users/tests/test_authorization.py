import urllib
import urlparse

from django.conf import settings
from linkedin import linkedin
from mock import patch
from protobufs.user_service_pb2 import UserService
import service.control

from services.test import (
    fuzzy,
    TestCase,
)

from .. import (
    factories,
    providers,
)


class TestAuthorization(TestCase):

    def setUp(self):
        self.client = service.control.Client('user')

    def test_get_authorization_instructions_linkedin(self):
        response = self.client.call_action(
            'get_authorization_instructions',
            provider=UserService.LINKEDIN,
        )
        self.assertTrue(response.success)
        self.assertTrue(response.result.authorization_url)

        url = urlparse.urlparse(response.result.authorization_url)
        params = dict(urlparse.parse_qsl(url.query))
        self.assertEqual(params['response_type'], 'code')
        self.assertEqual(params['redirect_uri'], settings.LINKEDIN_REDIRECT_URI)
        self.assertEqual(urllib.unquote(params['scope']), settings.LINKEDIN_SCOPE)
        self.assertEqual(params['client_id'], settings.LINKEDIN_CLIENT_ID)

        state = params['state']
        self.assertTrue(providers.valid_state_token(UserService.LINKEDIN, state))

    def test_complete_authorization_state_tampered(self):
        with self.assertFieldError('oauth2_details.state'):
            self.client.call_action(
                'complete_authorization',
                provider=UserService.LINKEDIN,
                oauth2_details={
                    'code': 'some-code',
                    'state': 'invalid',
                },
            )

    @patch('users.providers.linkedin.LinkedInApplication')
    @patch.object(providers.Linkedin, '_get_access_token')
    def test_complete_authorization_with_user(self, mocked_get_access_token, mocked_linkedin):
        mocked_get_access_token.return_value = (fuzzy.FuzzyUUID().fuzz(), 5184000)
        mocked_linkedin().get_profile.return_value = {
            'formattedName': 'Michael Hahn',
            'emailAddress': 'mwhahn@gmail.com',
            'id': fuzzy.FuzzyUUID().fuzz(),
        }
        user = factories.UserFactory.create_protobuf()
        response = self.client.call_action(
            'complete_authorization',
            provider=UserService.LINKEDIN,
            oauth2_details={
                'code': 'some-code',
                'state': providers.get_state_token(UserService.LINKEDIN),
            },
            user=user,
        )
        self.assertEqual(response.result.identity.provider, UserService.LINKEDIN)
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.user.primary_email, user.primary_email)

    def test_valid_state_token_quoted_characters(self):
        token = providers.get_state_token(UserService.LINKEDIN)
        # force encoding of periods
        token.replace('.', '%2E')
        self.assertTrue(providers.valid_state_token(UserService.LINKEDIN, token))

    @patch('users.providers.linkedin.LinkedInApplication')
    @patch.object(providers.Linkedin, '_get_access_token')
    def test_complete_authorization_linkedin_api_error(
            self,
            mocked_get_access_token,
            mocked_linkedin,
        ):
        mocked_get_access_token.return_value = (fuzzy.FuzzyUUID().fuzz(), 5184000)
        mocked_linkedin().get_profile.side_effect = linkedin.LinkedInError
        with self.assertRaises(self.client.CallActionError) as expected:
            self.client.call_action(
                'complete_authorization',
                provider=UserService.LINKEDIN,
                oauth2_details={
                    'code': 'some-code',
                    'state': providers.get_state_token(UserService.LINKEDIN),
                },
                user=factories.UserFactory.create_protobuf(),
            )

        response = expected.exception.response
        self.assertIn('PROVIDER_API_ERROR', response.errors)
