import arrow
from freezegun import freeze_time
from mock import patch
from rest_framework import status
from rest_framework.test import APIClient
from slacker import Response
from django.conf import settings
import textwrap

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .utils import (
    mock_slack_user_info,
    setup_mock_slack_test,
)
from ...slack.actions import (
    get_profile_for_slack_user,
    get_email_for_slack_user,
)
from ...slack.handlers.draft import LUNO_DRAFT_HELP
from ...slack.handlers.draft import actions


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

    def _request_payload(self, **overrides):
        payload = {
            'token': settings.SLACK_SLASH_COMMANDS_TOKEN,
            'user_id': fuzzy.FuzzyText().fuzz(),
            'team_id': fuzzy.FuzzyText().fuzz(),
            'command': '/luno',
            'text': '',
        }
        payload.update(overrides)
        return payload

    @patch('hooks.slack.actions.Slacker')
    def test_get_email_for_slack_user(self, patched):
        expected_email = mock_slack_user_info(patched)

        user_id = fuzzy.FuzzyUUID().fuzz()
        email = get_email_for_slack_user(self.slack_token, user_id)
        self.assertEqual(email, expected_email)

    @patch('hooks.slack.actions.Slacker')
    def test_get_profile_for_slack_user(self, patched):
        expected_profile = setup_mock_slack_test(self.mock, patched, self.organization)
        user_id = fuzzy.FuzzyUUID().fuzz()

        profile = get_profile_for_slack_user(
            self.token,
            self.slack_token,
            user_id,
        )
        self.verify_containers(expected_profile, profile)

    @patch('hooks.slack.actions.Slacker')
    def test_handle_draft_default_help_text(self, patched):
        setup_mock_slack_test(self.mock, patched, self.organization)
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

    def test_parse_draft_interval_last_x_messages(self):
        timestamp = arrow.utcnow().timestamp
        interval = actions.parse_draft_interval(timestamp, 'message')
        self.assertEqual(interval.messages, 1)
        self.assertIsNone(interval.from_timestamp)
        inputs = ['4 messages', '4 message', '4 msgs', '4']
        for i in inputs:
            interval = actions.parse_draft_interval(timestamp, i)
            self.assertIsNotNone(interval, i)
            self.assertEqual(interval.messages, 4, i)
            self.assertIsNone(interval.from_timestamp, i)

    def test_parse_draft_invalid_values(self):
        inputs = ['30 30 sec onds', '30seconds', '30min', '30minutes']
        for i in inputs:
            interval = actions.parse_draft_interval(arrow.utcnow().datetime, i)
            self.assertIsNone(interval, i)

    @patch('hooks.slack.handlers.draft.actions.Slacker')
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

    @patch('hooks.slack.handlers.draft.actions.Slacker')
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

    def test_replace_slack_links_with_post_links(self):
        txt = 'check this out '
        link = 'ftp://site.web/file.txt'
        link_text = 'File'
        slack_link = '<{link}>'.format(link=link)
        slack_link_with_link_text = '<{link}|{link_text}>'.format(link=link, link_text=link_text)
        post_link = '<a href={link}>{link}</a>'.format(link=link)
        post_link_with_link_text = '<a href={link}>{link_text}</a>'.format(link=link, link_text=link_text)
        txt_with_uid = '<@UA1B2C3> is here'

        self.assertEqual(actions.replace_slack_links_with_post_links(txt + slack_link), txt + post_link)
        self.assertEqual(actions.replace_slack_links_with_post_links(txt + slack_link_with_link_text), txt + post_link_with_link_text)
        self.assertEqual(actions.replace_slack_links_with_post_links(txt_with_uid), txt_with_uid)

    @patch('hooks.slack.handlers.draft.actions.Slacker')
    def test_replace_slack_uids_with_user_names(self, patched):
        token = 'a_token'
        name = 'john'
        uid = 'UA1B2C3'
        mock_slack_user_info(patched, name=name)
        txt_with_uid = 'hi <@{uid}>'.format(uid=uid)
        txt_with_uid_name = 'hi <@{uid}|{name}>'.format(uid=uid, name=name)
        txt_with_name = 'hi @' + name
        txt_with_link = 'check this out <ftp://site.web/file.txt>'

        self.assertEqual(actions.replace_slack_uids_with_user_names(token, txt_with_uid), txt_with_name)
        self.assertEqual(actions.replace_slack_uids_with_user_names(token, txt_with_uid_name), txt_with_name)
        self.assertEqual(actions.replace_slack_uids_with_user_names(token, txt_with_link), txt_with_link)

    def test_post_attachments_from_attachments(self):
        attachment = {
            'image_url': 'http://web.site/image.jpg',
            'url': 'http://web.site/image.jpg',
            'fallback': 'An image.',
            'image_width': 800,
            'image_height': 600,
        }
        expected_html = """
            <div>
                <a
                data-trix-attachment='{
                    "contentType":"image/jpeg",
                    "filename":"image.jpg",
                    "height":600,
                    "href":"http://web.site/image.jpg",
                    "url":"http://web.site/image.jpg",
                    "width":800
                }'
                data-trix-attributes='{
                    "caption":"An image."
                }'
                href="http://web.site/image.jpg"
                >
                    <figure
                    class="attachment attachment-preview"
                    >
                        <img
                        height="600"
                        src="http://web.site/image.jpg"
                        width="800"
                        >
                        <figcaption class="caption">
                            An image.
                        </figcaption>
                    </figure>
                </a>
            </div>"""
        expected_html = textwrap.dedent(expected_html).strip()

        post_attachments = actions.post_attachments_from_attachments([attachment])
        self.assertEqual(len(post_attachments), 1)
        self.assertEqual(post_attachments[0], expected_html)

    def test_post_attachment_from_file(self):
        file = {
            'permalink': 'http://web.site/page',
            'name': 'The name',
            'title': 'Some title.',
            'thumb_360': 'http://web.site/image.png',
            'thumb_360_w': 800,
            'thumb_360_h': 600,
            'mimetype': 'image/png',
        }
        expected_html = """
            <div>
                <a
                data-trix-attachment='{
                    "contentType":"image/png",
                    "filename":"The name",
                    "height":600,
                    "href":"http://web.site/image.png",
                    "url":"http://web.site/image.png",
                    "width":800
                }'
                data-trix-attributes='{
                    "caption":"Some title."
                }'
                href="http://web.site/page"
                >
                    <figure
                    class="attachment attachment-preview"
                    >
                        <img
                        height="600"
                        src="http://web.site/image.png"
                        width="800"
                        >
                        <figcaption class="caption">
                            Some title.
                        </figcaption>
                    </figure>
                </a>
            </div>"""
        expected_html = textwrap.dedent(expected_html).strip()

        self.assertEqual(actions.post_attachment_from_file(file), expected_html)

    def test_trix_image_attachment(self):
        details = {
            'url': 'http://some.url/image.png',
            'name': 'A name.',
            'width': 128,
            'height': 64,
            'caption': 'A caption.',
            'mime_type': 'image/png',
        }
        expected_html = """
            <div>
                <a
                data-trix-attachment='{
                    "contentType":"image/png",
                    "filename":"A name.",
                    "height":64,
                    "href":"http://some.url/image.png",
                    "url":"http://some.url/image.png",
                    "width":128
                }'
                data-trix-attributes='{
                    "caption":"A caption."
                }'
                href="http://some.url/image.png"
                >
                    <figure
                    class="attachment attachment-preview"
                    >
                        <img
                        height="64"
                        src="http://some.url/image.png"
                        width="128"
                        >
                        <figcaption class="caption">
                            A caption.
                        </figcaption>
                    </figure>
                </a>
            </div>"""
        expected_html = textwrap.dedent(expected_html).strip()

        self.assertEqual(actions.trix_image_attachment(**details), expected_html)

    @patch('hooks.slack.handlers.draft.actions.Slacker')
    def test_post_content_from_messages(self, patched):
        referenced_user_name = 'john'
        mock_slack_user_info(patched, name=referenced_user_name)
        first_message = {
            'user': 'a_user',
            'text': '<@U1A2B3C4> check this out: <http://some.site/page>',
            'attachments': [
                {
                    'image_url': 'http://some.site/image.jpg',
                    'url': 'http://some.site/page',
                    'fallback': 'An image.',
                    'image_width': 800,
                    'image_height': 600,
                }
            ],
        }
        second_message = {
            'user': 'another_user',
            'text': '<@U9G0D3G|jane> here\'s the file you wanted',
            'file': {
                'thumb_360': 'http://some.site/thumb.jpg',
                'thumb_360_w': 480,
                'thumb_360_h': 320,
                'permalink': 'http://some.site/image.jpg',
                'name': 'Some image',
                'title': 'Some title',
                'mimetype': 'image/jpeg',
            }
        }
        messages = [first_message, second_message]
        expected_html_first_msg_txt = '@john check this out: <a href=http://some.site/page>http://some.site/page</a>'
        expected_html_first_msg_attachment = """
            <div>
                <a
                data-trix-attachment='{
                    "contentType":"image/jpeg",
                    "filename":"image.jpg",
                    "height":600,
                    "href":"http://some.site/image.jpg",
                    "url":"http://some.site/image.jpg",
                    "width":800
                }'
                data-trix-attributes='{
                    "caption":"An image."
                }'
                href="http://some.site/image.jpg"
                >
                    <figure
                    class="attachment attachment-preview"
                    >
                        <img
                        height="600"
                        src="http://some.site/image.jpg"
                        width="800"
                        >
                        <figcaption class="caption">
                            An image.
                        </figcaption>
                    </figure>
                </a>
            </div>"""
        expected_html_second_msg_txt = '@jane here\'s the file you wanted'
        expected_html_second_msg_file = """
            <div>
                <a
                data-trix-attachment='{
                    "contentType":"image/jpeg",
                    "filename":"Some image",
                    "height":320,
                    "href":"http://some.site/thumb.jpg",
                    "url":"http://some.site/thumb.jpg",
                    "width":480
                }'
                data-trix-attributes='{
                    "caption":"Some title"
                }'
                href="http://some.site/image.jpg"
                >
                    <figure
                    class="attachment attachment-preview"
                    >
                        <img
                        height="320"
                        src="http://some.site/thumb.jpg"
                        width="480"
                        >
                        <figcaption class="caption">
                            Some title
                        </figcaption>
                    </figure>
                </a>
            </div>"""
        expected_html = ''.join([
            expected_html_first_msg_txt,
            textwrap.dedent(expected_html_first_msg_attachment).strip(),
            '<br>',
            expected_html_second_msg_txt,
            textwrap.dedent(expected_html_second_msg_file).strip(),
            '<br><br>',
        ])

        self.assertEqual(actions.post_content_from_messages('a_token', messages), expected_html)
