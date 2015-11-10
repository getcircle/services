from rest_framework import exceptions
from rest_framework.response import Response

from .draft import handle_draft
from .search import handle_search


LUNO_HELP = """
Valid commands: draft
To start a draft in luno: /luno draft last 5 minutes
"""


def handle_hook(request):
    command = request.data['command']
    handler = COMMAND_TO_HANDLER_MAP.get(command)
    if not handler:
        raise exceptions.NotFound(detail='Don\'t know how to handle: %s' % (command,))

    return handler(request)


def handle_luno_command(request):
    try:
        action, text = request.data['text'].split(' ', 1)
    except ValueError:
        action = request.data['text']
        text = ''

    handler = ACTION_TO_HANDLER_MAP.get(action)
    if not handler:
        return Response({'text': LUNO_HELP})

    return handler(request, text)


COMMAND_TO_HANDLER_MAP = {
    '/luno': handle_luno_command,
}

ACTION_TO_HANDLER_MAP = {
    'draft': handle_draft,
    'search': handle_search,
}
