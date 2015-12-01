from mock import patch
from protobufs.services.organization.containers import integration_pb2
from rest_framework import status
from rest_framework.test import APIClient
from slacker import Response

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from ...slack.handlers import LUNO_HELP


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.slack_token = fuzzy.FuzzyText().fuzz()
        self.api = APIClient()

    def _setup_test(self, patched):
        patched().users.info.return_value = Response(
            '{"ok": true, "user": {"profile": {"email": "%s"}}}' % (self.profile.email,)
        )
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=self.profile,
            return_object_path='profile',
            email=self.profile.email,
        )

    def test_slack_hooks_slash_integration_doesnt_exist(self):
        slack_token = fuzzy.FuzzyText().fuzz()
        error = self.mock.get_mockable_call_action_error('organization', 'get_integration')
        self.mock.instance.register_mock_error(
            service='organization',
            action='get_integration',
            error=error,
            provider_uid=slack_token,
            integration_type=integration_pb2.SLACK_SLASH_COMMAND,
        )
        response = self.api.post('/hooks/slack/', {'token': slack_token})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_slack_hooks_slack_api_integration_doesnt_exist(self):
        error = self.mock.get_mockable_call_action_error('organization', 'get_integration')
        self.mock.instance.register_mock_error(
            service='organization',
            action='get_integration',
            error=error,
            integration_type=integration_pb2.SLACK_WEB_API,
        )
        response = self.api.post('/hooks/slack/', {'token': fuzzy.FuzzyText().fuzz()})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('hooks.slack.actions.Slacker')
    def test_slack_hooks_profile_not_found(self, patched):
        expected_email = 'test@acme.com'
        patched().users.info.return_value = Response(
            '{"ok": true, "user": {"profile": {"email": "%s"}}}' % (expected_email,)
        )
        error = self.mock.get_mockable_call_action_error('profile', 'get_profile')
        self.mock.instance.register_mock_error(
            service='profile',
            action='get_profile',
            error=error,
            email=expected_email,
            inflations={'enabled': False},
        )
        response = self.api.post('/hooks/slack/', {
            'token': fuzzy.FuzzyText().fuzz(),
            'user_id': fuzzy.FuzzyText().fuzz(),
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('hooks.slack.actions.Slacker')
    def test_slack_hooks_luno_help(self, patched):
        self._setup_test(patched)
        response = self.api.post('/hooks/slack/', {
            'token': fuzzy.FuzzyText().fuzz(),
            'user_id': fuzzy.FuzzyText().fuzz(),
            'command': '/luno',
            'text': '',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], LUNO_HELP)
