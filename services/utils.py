import urllib
import uuid

import arrow
from django.conf import settings
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
