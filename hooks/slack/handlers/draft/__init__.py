from protobufs.services.post import containers_pb2 as post_containers
from rest_framework.response import Response
import service.control

from hooks.helpers import get_post_resource_url
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
    title = 'Slack Draft - %s' % (text,)
    content = actions.post_content_from_messages(request.slack_api_token, messages)
    post = service.control.get_object(
        service='post',
        action='create_post',
        return_object='post',
        client_kwargs={'token': request.token},
        post={
            'title': title,
            'content': content,
            'source': post_containers.SLACK,
        },
    )
    response_url = get_post_resource_url(request.organization.domain, post, edit=True)
    return Response({'text': 'Draft created: %s' % (response_url,)})
