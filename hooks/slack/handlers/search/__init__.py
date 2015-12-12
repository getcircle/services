import json
import logging
import requests

from protobuf_to_dict import protobuf_to_dict
from rest_framework.response import Response
import service.control

from . import actions

LUNO_SEARCH_HELP = """
Usage: To search within luno: /luno search <query>
"""

logger = logging.getLogger(__name__)


def handle_search(request, text):
    text = text.strip()
    if not text:
        return Response({'text': LUNO_SEARCH_HELP})

    results = service.control.get_object(
        service='search',
        action='search_v2',
        return_object='results',
        client_kwargs={'token': request.token},
        query=text,
    )
    attachments = []
    for result in results:
        attachment = actions.result_to_slack_attachment(result)
        if not attachment:
            logger.warn('no attachment found for: %s' % (protobuf_to_dict(result),))
            continue
        attachments.append(attachment)

    if attachments:
        requests.post(request.data['response_url'], data=json.dumps({'attachments': attachments}))
        return Response()
    else:
        logger.warn('no search results found for: %s' % (text,))
        return Response({'text': 'No search results found'})
