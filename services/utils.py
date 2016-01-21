import json
import urllib
import uuid

import arrow
from django.conf import settings
import requests
import service.control

PAGE_SIZE = 100


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


def execute_handler_on_paginated_items(
        token,
        service_name,
        action,
        return_object_path,
        handler,
        action_kwargs=None,
        **kwargs
    ):
    if not action_kwargs:
        action_kwargs = {}

    client = service.control.Client(service_name, token=token)
    next_page = 1
    while next_page:
        response = client.call_action(
            action,
            control={'paginator': {'page': next_page, 'page_size': PAGE_SIZE}},
            **action_kwargs
        )
        items = getattr(response.result, return_object_path)
        if not items:
            print 'no items found for %s:%s' % (service_name, action)
            break

        handler(items, token=token, **kwargs)
        if response.control.paginator.page != response.control.paginator.total_pages:
            next_page = response.control.paginator.next_page
        else:
            break


def has_field_error(response, field, error):
    """Determine whether or not the response has the given field error.

    Args:
        response (service.control.Response): service response
        field (str): name of the field
        error (str): error code

    Returns:
        bool: True if the response has the field error, False if not.

    """
    error_details = response.error_details or []
    errors = response.errors or []
    if 'FIELD_ERROR' not in errors:
        return False

    has_error = False
    for error_detail in error_details:
        if (
            error_detail.key == field and
            error_detail.detail == error and
            error_detail.error == 'FIELD_ERROR'
        ):
            has_error = True
            break
    return has_error
