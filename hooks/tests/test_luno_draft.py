import arrow
from freezegun import freeze_time
from mock import patch
from rest_framework import status
from rest_framework.test import APIClient
from slacker import Response

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import actions
from ..handlers import LUNO_DRAFT_HELP


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

    def _mock_user_info(self, patched, email='test@acme.com'):
        patched().users.info.return_value = Response(
            '{"ok": true, "user": {"profile": {"email": "%s"}}}' % (email,)
        )
        return email

    def _setup_test(self, patched):
        expected_email = self._mock_user_info(patched)
        expected_profile = mocks.mock_profile(
            organization_id=self.organization.id,
            email=expected_email,
        )
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=expected_profile,
            return_object_path='profile',
            email=expected_email,
            inflations={'enabled': False},
        )
        return expected_profile

    def _request_payload(self, **overrides):
        payload = {
            'token': fuzzy.FuzzyText().fuzz(),
            'user_id': fuzzy.FuzzyText().fuzz(),
            'command': '/luno',
            'text': '',
        }
        payload.update(overrides)
        return payload

    @patch('hooks.actions.Slacker')
    def test_get_email_for_slack_user(self, patched):
        expected_email = self._mock_user_info(patched)

        user_id = fuzzy.FuzzyUUID().fuzz()
        email = actions.get_email_for_slack_user(self.slack_token, user_id)
        self.assertEqual(email, expected_email)

    @patch('hooks.actions.Slacker')
    def test_get_profile_for_slack_user(self, patched):
        expected_profile = self._setup_test(patched)
        user_id = fuzzy.FuzzyUUID().fuzz()

        profile = actions.get_profile_for_slack_user(
            self.token,
            self.slack_token,
            user_id,
        )
        self.verify_containers(expected_profile, profile)

    @patch('hooks.actions.Slacker')
    def test_handle_draft_default_help_text(self, patched):
        self._setup_test(patched)
        response = self.api.post('/hooks/slack/', self._request_payload(text='draft'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], LUNO_DRAFT_HELP)

    @freeze_time('2015-11-10 09:30:00')
    def test_parse_draft_interval_minutes(self):
        inputs = ['5 minutes', '5m', '5 min', '5 mins']
        for i in inputs:
            interval = actions.parse_draft_interval(arrow.utcnow().datetime, i)
            self.assertEqual(interval.from_timestamp, 1447147500)
            self.assertIsNone(interval.messages)

    @freeze_time('2015-11-10 09:30:00')
    def test_parse_draft_interval_seconds(self):
        inputs = ['30 seconds', '30 secs', '30 sec', '30s']
        for i in inputs:
            interval = actions.parse_draft_interval(arrow.utcnow().datetime, i)
            self.assertEqual(interval.from_timestamp, 1447147770)
            self.assertIsNone(interval.messages)

    def test_parse_draft_invalid_values(self):
        inputs = ['30 30 sec onds', '30seconds', '30min', '30minutes']
        for i in inputs:
            interval = actions.parse_draft_interval(arrow.utcnow().datetime, i)
            self.assertIsNone(interval, i)

    @patch('hooks.actions.Slacker')
    @freeze_time('2015-11-10 09:30:00')
    def test_get_messages_for_interval_last_5_minutes(self, patched):
        patched().channels.history.return_value = Response(
            '{"has_more": false, "ok": true, "oldest": "1447146812", "messages": [{"text": "`posts`", "type": "message", "ts": "1447146964.000316", "user": "U03LRM1A9"}, {"text": "i don\\u2019t see the post chagnes on master", "type": "message", "ts": "1447146815.000315", "user": "U03LRKMJX"}], "is_limited": false}'
        )

        request_time = arrow.utcnow().timestamp
        channel_id = fuzzy.FuzzyText().fuzz()
        draft_interval = actions.parse_draft_interval(request_time, '5 minutes')
        messages = actions.get_messages_for_interval(
            fuzzy.FuzzyUUID().fuzz(),
            request_time,
            channel_id,
            draft_interval,
            'eng',
        )
        self.assertEqual(len(messages), 2)
        args, kwargs = patched().channels.history.call_args_list[0]
        self.assertEqual(args[0], channel_id)
        self.assertEqual(kwargs['oldest'], 1447147500)
        self.assertEqual(kwargs['latest'], 1447147800)

    @patch('hooks.actions.Slacker')
    @freeze_time('2015-11-10 09:30:00')
    def test_get_messages_for_interval_last_5_minutes_private_group(self, patched):
        patched().groups.history.return_value = Response(
            '{"has_more": false, "ok": true, "oldest": "1447146812", "messages": [{"text": "`posts`", "type": "message", "ts": "1447146964.000316", "user": "U03LRM1A9"}, {"text": "i don\\u2019t see the post chagnes on master", "type": "message", "ts": "1447146815.000315", "user": "U03LRKMJX"}], "is_limited": false}'
        )

        request_time = arrow.utcnow().timestamp
        channel_id = fuzzy.FuzzyText().fuzz()
        draft_interval = actions.parse_draft_interval(request_time, '5 minutes')
        messages = actions.get_messages_for_interval(
            fuzzy.FuzzyUUID().fuzz(),
            request_time,
            channel_id,
            draft_interval,
            'privategroup',
        )
        self.assertEqual(len(messages), 2)
        args, kwargs = patched().groups.history.call_args_list[0]
        self.assertEqual(args[0], channel_id)
        self.assertEqual(kwargs['oldest'], 1447147500)
        self.assertEqual(kwargs['latest'], 1447147800)
