import urllib
import urlparse

from django.conf import settings
from linkedin import linkedin
from mock import patch
from protobufs.user_service_pb2 import UserService
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)
from services.token import parse_token

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
        payload = providers.parse_state_token(UserService.LINKEDIN, state)
        self.assertTrue(payload['csrftoken'])

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
    @patch.object(providers.LinkedIn, '_get_access_token')
    def test_complete_authorization_with_user(self, mocked_get_access_token, mocked_linkedin):
        mocked_get_access_token.return_value = (fuzzy.FuzzyUUID().fuzz(), 5184000)
        mocked_linkedin().get_profile.return_value = {
            'formattedName': 'Michael Hahn',
            'emailAddress': 'mwhahn@gmail.com',
            'id': fuzzy.FuzzyUUID().fuzz(),
            'skills': {
                'values': [
                    {'skill': {'name': 'Python'}, 'id': 42},
                    {'skill': {'name': 'MySQL'}, 'id': 43},
                ],
            },
        }
        user = factories.UserFactory.create_protobuf()
        self.client.token = mocks.mock_token(user_id=user.id)
        parsed_token = parse_token(self.client.token)
        with self.default_mock_transport(self.client) as mock:
            mock_response = mock.get_mockable_response('profile', 'add_skills')
            mock.instance.register_mock_response(
                'profile',
                'add_skills',
                mock_response,
                profile_id=parsed_token.profile_id,
                skills=[{'name': 'Python'}, {'name': 'MySQL'}],
            )
            response = self.client.call_action(
                'complete_authorization',
                provider=UserService.LINKEDIN,
                oauth2_details={
                    'code': 'some-code',
                    'state': providers.get_state_token(UserService.LINKEDIN, {}),
                },
            )
        self.assertEqual(response.result.identity.provider, UserService.LINKEDIN)
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.user.primary_email, user.primary_email)

    def test_valid_state_token_quoted_characters(self):
        expected = {'token': mocks.mock_token()}
        token = providers.get_state_token(UserService.LINKEDIN, expected)
        # force encoding of periods
        token.replace('.', '%2E')
        payload = providers.parse_state_token(UserService.LINKEDIN, token)
        self.assertEqual(payload['token'], expected['token'])

    @patch('users.providers.linkedin.LinkedInApplication')
    @patch.object(providers.LinkedIn, '_get_access_token')
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
                    'state': providers.get_state_token(UserService.LINKEDIN, {}),
                },
            )

        response = expected.exception.response
        self.assertIn('PROVIDER_API_ERROR', response.errors)

    @patch('users.providers.linkedin.LinkedInApplication')
    @patch.object(providers.LinkedIn, '_get_access_token')
    def test_complete_authorization_no_user(self, mocked_get_access_token, mocked_linkedin):
        mocked_get_access_token.return_value = (fuzzy.FuzzyUUID().fuzz(), 5184000)
        mocked_linkedin().get_profile.return_value = {
            'formattedName': 'Michael Hahn',
            'emailAddress': 'mwhahn@gmail.com',
            'id': fuzzy.FuzzyUUID().fuzz(),
        }
        response = self.client.call_action(
            'complete_authorization',
            provider=UserService.LINKEDIN,
            oauth2_details={
                'code': 'some-code',
                'state': providers.get_state_token(UserService.LINKEDIN, {}),
            },
        )
        self.assertEqual(response.result.identity.provider, UserService.LINKEDIN)
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertEqual(response.result.user.primary_email, 'mwhahn@gmail.com')

    @patch('users.providers.linkedin.LinkedInApplication')
    @patch.object(providers.LinkedIn, '_get_access_token')
    def test_complete_authorization_identity_exists(
            self,
            mocked_get_access_token,
            mocked_linkedin,
        ):
        mocked_get_access_token.return_value = (fuzzy.FuzzyUUID().fuzz(), 5184000)
        linkedin_id = fuzzy.FuzzyUUID().fuzz()
        mocked_linkedin().get_profile.return_value = {
            'formattedName': 'Michael Hahn',
            'emailAddress': 'mwhahn@gmail.com',
            'id': linkedin_id,
        }
        identity = factories.IdentityFactory.create_protobuf(
            access_token='old',
            provider_uid=linkedin_id,
        )
        self.client.token = mocks.mock_token(user_id=identity.user_id)
        response = self.client.call_action(
            'complete_authorization',
            provider=UserService.LINKEDIN,
            oauth2_details={
                'code': 'some-code',
                'state': providers.get_state_token(UserService.LINKEDIN, {}),
            },
        )
        self.assertEqual(response.result.identity.provider, UserService.LINKEDIN)
        self.assertEqual(response.result.identity.email, 'mwhahn@gmail.com')
        self.assertEqual(response.result.identity.full_name, 'Michael Hahn')
        self.assertNotEqual(response.result.identity.access_token, 'old')
        self.assertTrue(response.result.identity.access_token)