from collections import namedtuple
import re

import arrow
from slacker import Slacker

TIME_INTERVALS = {
    'minutes': ['minutes', 'min', 'mins', 'm'],
    'seconds': ['seconds', 'secs', 'sec', 's'],
}
VALID_TIME_INTERVALS = sum(TIME_INTERVALS.values(), [])
VALID_MESSAGE_ALIASES = ['messages', 'msgs', 'message']
DraftInterval = namedtuple('DraftInterval', ['from_timestamp', 'messages'])


def get_messages_for_interval(
        slack_api_token,
        latest_timestamp,
        channel_id,
        draft_interval,
        channel_name,
    ):
    slack = Slacker(slack_api_token)
    parameters = {'latest': latest_timestamp, 'count': 1000}
    if draft_interval.from_timestamp:
        parameters['oldest'] = draft_interval.from_timestamp
    elif draft_interval.messages:
        # TODO if this is over a 1000 this would fail, not sure if we want to
        # raise an error message
        parameters['count'] = draft_interval.messages

    endpoint = 'channels'
    if channel_name == 'privategroup':
        endpoint = 'groups'

    response = getattr(slack, endpoint).history(channel_id, **parameters)
    if response.successful:
        return response.body['messages']


def _parse_time_interval(request_time, interval, interval_type):
    interval = -int(interval)
    parameters = {}

    for key, values in TIME_INTERVALS.iteritems():
        if interval_type in values:
            parameters[key] = interval

    if parameters:
        return DraftInterval(arrow.get(request_time).replace(**parameters).timestamp, None)


def _parse_multipart_interval(request_time, parts):
    interval, interval_type = parts
    if not interval.isdigit():
        return None

    if interval_type in VALID_TIME_INTERVALS:
        return _parse_time_interval(
            request_time,
            interval,
            interval_type,
        )
    elif interval_type in VALID_MESSAGE_ALIASES:
        return DraftInterval(None, int(interval))


def _parse_interval(request_time, parts):
    interval = ''
    part = parts[0]
    if part == 'message':
        return DraftInterval(None, 1)

    for index, char in enumerate(part):
        is_last_char = index == len(part) - 1
        if char.isdigit():
            interval += char
            if is_last_char:
                return DraftInterval(None, int(interval))
        elif is_last_char and char in VALID_TIME_INTERVALS:
            return _parse_time_interval(
                request_time,
                interval,
                char,
            )
        else:
            break


def parse_draft_interval(request_time, text):
    parts = text.split(' ', 1)
    draft_interval = None
    if len(parts) > 1:
        draft_interval = _parse_multipart_interval(request_time, parts)
    else:
        draft_interval = _parse_interval(request_time, parts)
    return draft_interval


def post_content_from_messages(slack_api_token, messages):
    content = []
    prev_author = None
    for message in messages:
        if 'text' in message:
            text = replace_slack_links_with_post_links(message['text'])
            text = replace_slack_uids_with_user_names(slack_api_token, text)
            content.append(text)
            author = None
            if 'user' in message:
                author = message['user']
            if prev_author != None and author != prev_author:
                content.append('<br><br>')
            else:
                content.append('<br>')
            prev_author = author
    return ''.join(content)


def replace_slack_links_with_post_links(text):
    # Catch both kinds of Slack links
    # with link text: <http://lunohq.com|Luno>
    # without link text: <http://lunohq.com>
    new_text = re.sub(r'<([^@\s]+\://\S+)\|(\S+)>', r'<a href=\1>\2</a>', text)
    new_text = re.sub(r'<([^@\s]+\://\S+)>', r'<a href=\1>\1</a>', new_text)
    return new_text


def replace_slack_uids_with_user_names(slack_api_token, text):
    user_names = {}
    slack = Slacker(slack_api_token)
    def user_name_for_slack_uid_match(match):
        uid = match.group(1)
        if uid in user_names:
            return user_names[uid]
        else:
            try:
                response = slack.users.info(uid)
                if response.successful:
                    name = '@' + response.body['user']['name']
                    user_names[uid] = name
                    return name
            except:
                # Probably couldn't find user because match turned out not to be an ID
                # Just return match with '@' prefixed because it was outside the capture group
                return '@' + uid

    new_text = re.sub(r'<@(\w+)>', user_name_for_slack_uid_match, text)
    return new_text
