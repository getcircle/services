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
            if 'attachments' in message:
                content.extend(post_attachments_from_attachments(message['attachments']))
            if 'file' in message:
                content.append(post_attachment_from_file(message['file']))
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

    # Some user references (such as those in messages which contain a file) have the name embedded.
    new_text = re.sub(r'<@\w+\|(\w+)>', r'@\1', text)
    new_text = re.sub(r'<@(\w+)>', user_name_for_slack_uid_match, new_text)
    return new_text


def post_attachments_from_attachments(attachments):
    post_attachments = []
    for attachment in attachments:
        if 'image_url' in attachment:
            url = attachment['image_url']
            details = {
                'url': url,
                'name': url.rsplit('/', 1)[-1],
                'caption': attachment.get('fallback', ''),
                'width': attachment.get('image_width', 0),
                'height': attachment.get('image_height', 0),
                'mime_type': 'image/jpeg',
            }
            html = trix_image_attachment(**details)
            post_attachments.append(html)
    return post_attachments


def post_attachment_from_file(file):
    html = ''
    if 'thumb_360' in file:
        details = {
            'thumbnail_url': file['thumb_360'],
            'url': file['permalink'],
            'name': file.get('name', ''),
            'width': file.get('thumb_360_w', 0),
            'height': file.get('thumb_360_h', 0),
            'caption': file.get('title', ''),
            'mime_type': file.get('mimetype', ''),
        }
        html = trix_image_attachment(**details)
    return html


def trix_image_attachment(url, name, caption, width, height, mime_type, thumbnail_url=None):
    details = {
        'thumbnail_url': thumbnail_url if thumbnail_url != None else url,
        'url': url,
        'name': name,
        'width': width,
        'height': height,
        'caption': caption,
        'mime_type': mime_type,
    }
    return """
        <div>
            <a
            data-trix-attachment='{{
                "contentType":"{mime_type}",
                "filename":"{name}",
                "height":{height},
                "href":"{thumbnail_url}",
                "url":"{thumbnail_url}",
                "width":{width}
            }}'
            data-trix-attributes='{{
                "caption":"{caption}"
            }}'
            href="{url}"
            >
                <figure
                class="attachment attachment-preview"
                >
                    <img
                    height="{height}"
                    src="{thumbnail_url}"
                    width="{width}"
                    >
                    <figcaption class="caption">
                        {caption}
                    </figcaption>
                </figure>
            </a>
        </div>""".format(**details)
