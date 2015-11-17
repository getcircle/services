import urlparse

from django.conf import settings
from rest_framework.response import Response
import service.control

from . import actions

LUNO_DRAFT_HELP = """
Usage: To start a draft in luno: /luno draft <message interval>
"""


def handle_draft(request, text):
    # text value should be of the format "last <message interval>"
    try:
        _, interval = text.split(' ', 1)
    except ValueError:
        return Response({'text': LUNO_DRAFT_HELP})

    draft_interval = actions.parse_draft_interval(request.start_timestamp, interval)
    messages = actions.get_messages_for_interval(
        slack_api_token=request.slack_api_token,
        latest_timestamp=request.start_timestamp,
        channel_id=request.data['channel_id'],
        draft_interval=draft_interval,
        channel_name=request.data['channel_name'],
    )
    messages.reverse()
    # XXX should have a `post_content_from_messages` function, we should handle
    # special formatting for the messages
    text_values = [m['text'] for m in messages if 'text' in m and 'subtype' not in m]
    title = 'Slack Draft - %s' % (text,)
    content = '\n'.join(text_values)
    post = service.control.get_object(
        service='post',
        action='create_post',
        return_object='post',
        client_kwargs={'token': request.token},
        post={'title': title, 'content': content},
    )
    parsed_url = urlparse.urlparse(settings.FRONTEND_URL)
    # XXX the frontend should support different actions, ie:
        # post_created_from_slack or something so that we don't have to know
        # about the URL structure of the app, we just send an event that
        # happend and it needs to handle routing to the correct location
    parsed_url = parsed_url._replace(path='/'.join(['post', post.id, 'edit']))
    response_url = urlparse.urlunparse(parsed_url)
    return Response({'text': 'Draft created: %s' % (response_url,)})