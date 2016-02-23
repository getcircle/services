from collections import namedtuple

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


def post_content_from_messages(messages):
    text_values = [m['text'] for m in messages if 'text' in m]
    return '\n'.join(text_values)
