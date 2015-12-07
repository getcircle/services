from collections import namedtuple
import logging
import os

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from flanker import mime
from protobufs.services.post import containers_pb2 as post_containers
import service.control

logger = logging.getLogger(__file__)

SourceDetails = namedtuple('SourceDetails', ('profile_id', 'organization_id'))


def _get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _get_unprocessed_key(message_id):
    return os.path.join(settings.EMAIL_HOOK_UNPROCESSED_KEY_PREFIX, message_id)


def _get_processed_key(message_id):
    return os.path.join(settings.EMAIL_HOOK_PROCESSED_KEY_PREFIX, message_id)


def get_details_for_source(domain, source):
    response = service.control.call_action(
        service='profile',
        action='profile_exists',
        domain=domain,
        email=source,
    )
    if response.result.exists:
        return SourceDetails(response.result.profile_id, response.result.organization_id)


def get_post_from_message(message_id, draft=False):
    client = _get_s3_client()
    key = _get_unprocessed_key(message_id)
    try:
        response = client.get_object(Bucket=settings.EMAIL_HOOK_S3_BUCKET, Key=key)
    except ClientError as e:
        logger.exception('Error fetching object: %s', e)
        return None

    try:
        body = response['Body'].read()
    except KeyError:
        logger.exception('invalid response from s3: %s', body)
        return None

    try:
        message = mime.from_string(body)
    except mime.DecodingError as e:
        logger.exception('failed to parse message body: %s', e)
        return None

    plain_text = None
    for part in message.parts:
        if part.content_type.value == 'text/plain':
            plain_text = part.body
            break

    # TODO should be handling empty subjects or bodies by notifying the user it
    # failed to parse
    if not plain_text or not message.subject:
        if not message.subject:
            logger.error('message subject is required to create a post')
        else:
            logger.error('only plain text is supported currently')
        return None

    state = post_containers.DRAFT if draft else post_containers.LISTED
    return post_containers.PostV1(
        title=message.subject,
        content=plain_text,
        state=state,
    )


def mark_message_as_processed(message_id):
    client = _get_s3_client()
    unprocessed_key = _get_unprocessed_key(message_id)
    processed_key = _get_processed_key(message_id)
    try:
        response = client.copy_object(
            Bucket=settings.EMAIL_HOOK_S3_BUCKET,
            Key=processed_key,
            CopySource=unprocessed_key,
        )
    except ClientError as e:
        logger.exception('Error copying object: %s', e)
        raise

    if 'CopyObjectResult' not in response:
        logger.exception('Unknown response: %s', response)
        raise ValueError('Unknown response: %s' % (response,))

    try:
        response = client.delete_object(
            Bucket=settings.EMAIL_HOOK_S3_BUCKET,
            Key=unprocessed_key,
        )
    except ClientError as e:
        logger.exception('Error deleting object: %s', e)
        raise

    if 'DeleteMarker' not in response or not response['DeleteMarker']:
        logger.exception('Unknown response: %s', response)
        raise ValueError('Unknown response: %s' % (response,))
