import json
from mock import patch
from rest_framework import status
from rest_framework.test import APIClient

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .utils import setup_mock_slack_test
from ...slack.handlers.search import LUNO_SEARCH_HELP
from ...slack.handlers.search import actions


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.api = APIClient()
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object=self.organization,
            return_object_path='organization',
            mock_regex_lookup='organization:get_organization.*',
        )

    def _request_payload(self, **overrides):
        payload = {
            'token': fuzzy.FuzzyText().fuzz(),
            'user_id': fuzzy.FuzzyText().fuzz(),
            'command': '/luno',
            'response_url': fuzzy.FuzzyText(prefix='https://').fuzz(),
            'text': '',
        }
        payload.update(overrides)
        return payload

    @patch('hooks.slack.actions.Slacker')
    def test_handle_search_default_help_text(self, patched):
        setup_mock_slack_test(self.mock, patched, self.organization)
        response = self.api.post('/hooks/slack/', self._request_payload(text='search'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], LUNO_SEARCH_HELP)

    @patch('hooks.slack.actions.Slacker')
    def test_handle_search_default_help_text_strip_text(self, patched):
        setup_mock_slack_test(self.mock, patched, self.organization)
        response = self.api.post('/hooks/slack/', self._request_payload(text='search    '))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], LUNO_SEARCH_HELP)

    def test_result_to_slack_attachment_profile(self):
        profile = mocks.mock_profile(display_title=fuzzy.FuzzyText().fuzz())
        result = mocks.mock_search_result(profile=profile)
        attachment = actions.result_to_slack_attachment(self.organization.domain, result)
        pretext = '%s (%s): %s' % (
            profile.full_name,
            profile.display_title,
            actions.get_profile_resource_url(self.organization.domain, profile),
        )
        self.assertEqual(attachment['fallback'], pretext)
        self.assertEqual(attachment['pretext'], pretext)

    @patch('hooks.slack.actions.Slacker')
    def test_handle_search_no_results(self, patched):
        setup_mock_slack_test(self.mock, patched, self.organization)
        response = self.api.post('/hooks/slack/', self._request_payload(text='search None'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'No search results found')

    @patch('hooks.slack.handlers.search.requests')
    @patch('hooks.slack.actions.Slacker')
    def test_handle_search_profiles(self, patched, patched_requests):
        setup_mock_slack_test(self.mock, patched, self.organization)
        profile = mocks.mock_profile(display_title=fuzzy.FuzzyText().fuzz())
        self.mock.instance.register_mock_object(
            service='search',
            action='search_v2',
            return_object_path='results',
            return_object=[mocks.mock_search_result(profile=profile)],
            query='Ralph',
        )
        response = self.api.post('/hooks/slack/', self._request_payload(text='search Ralph'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = json.loads(patched_requests.post.call_args[1]['data'])
        attachment = payload['attachments'][0]
        self.assertEqual(
            actions.profile_to_slack_attachment(self.organization.domain, profile),
            attachment,
        )
