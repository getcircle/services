import json
import urllib
import uuid

import arrow
from django.conf import settings
from protobuf_to_dict import dict_to_protobuf
from protobufs.services.common import containers_pb2 as common_containers
import requests


def matching_uuids(first, second, version=4):
    try:
        if not isinstance(first, uuid.UUID):
            first = uuid.UUID(first, version=version)
        if not isinstance(second, uuid.UUID):
            second = uuid.UUID(second, version=version)
    except ValueError:
        return False
    return first == second


def get_timezone_for_location(latitude, longitude):
    parameters = {
        'timestamp': arrow.utcnow().timestamp,
        'key': settings.GOOGLE_API_KEY,
        'location': '%s,%s' % (latitude, longitude),
    }
    endpoint = '%s?%s' % (settings.GOOGLE_TIMEZONE_ENDPOINT, urllib.urlencode(parameters))
    response = requests.get(endpoint)
    if not response.ok:
        raise ValueError('Failed to update timezone: %s' % (response.content,))
    return response.json()['timeZoneId']


def should_inflate_field(field_name, inflations):
    if isinstance(inflations, dict):
        inflations = dict_to_protobuf(inflations, common_containers.InflationsV1)

    should_inflate = True
    if inflations:
        if (
            not inflations.enabled or
            (inflations.exclude and field_name in inflations.exclude) or
            (inflations.only and field_name not in inflations.only) or
            inflations.disabled
        ):
            should_inflate = False
    return should_inflate


def build_slack_message(attachments, channel, username=None, icon_emoji=None):
    if icon_emoji is None:
        icon_emoji = ':cubimal_chick:'

    if username is None:
        username = 'sns-bot'

    return json.dumps({
        'channel': channel,
        'icon_emoji': icon_emoji,
        'username': username,
        'attachments': attachments,
    })
