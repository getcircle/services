from collections import namedtuple
import logging
import os

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from flanker import mime
from protobufs.services.post import containers_pb2 as post_containers
import service.control
import tldextract

from hooks.helpers import (
    get_post_resource_url,
    get_root_url,
)

from .translators.trix import translate_html

logger = logging.getLogger(__name__)

SourceDetails = namedtuple('SourceDetails', ('email', 'profile_id', 'organization_id', 'domain'))


class Attachment(object):

    def __init__(self, mime):
        self.mime = mime
        self.file = None


def _get_boto_client(client_type, **kwargs):
    return boto3.client(
        client_type,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        **kwargs
    )


def _get_unprocessed_key(message_id):
    return os.path.join(settings.EMAIL_HOOK_UNPROCESSED_KEY_PREFIX, message_id)


def _get_processed_key(message_id):
    return os.path.join(settings.EMAIL_HOOK_PROCESSED_KEY_PREFIX, message_id)


def extract_domain(source, recipient):
    """Extract the domain from either the source address or the recipient address"""
    # by default tldextract makes a web request when first initializes and
    # uses a cache file, disable these and just use the default snapshot it
    # comes with
    extract = tldextract.TLDExtract(suffix_list_url=False, cache_file=False)
    extracted = extract(recipient)
    if extracted.subdomain:
        domain = extract(recipient).subdomain.split('.')[0]
        if domain != 'mail':
            return domain

    extracted = extract(source)
    return extracted.domain


def get_details_for_source(domain, source):
    response = service.control.call_action(
        service='profile',
        action='profile_exists',
        domain=domain,
        email=source,
    )
    if response.result.exists:
        return SourceDetails(
            email=source,
            profile_id=response.result.profile_id,
            organization_id=response.result.organization_id,
            domain=domain,
        )


def upload_attachment(attachment, token):
    name = attachment.content_type.params.get('name', 'unnamed')
    response = service.control.call_action(
        service='file',
        action='upload',
        client_kwargs={'token': token},
        file={
            'name': name,
            'content_type': attachment.content_type.value,
            'bytes': str(attachment.body),
        },
    )
    return response.result.file


def _get_message(message_id):
    client = _get_boto_client('s3')
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
    return message


def get_post_from_message(message_id, token, draft=False):
    message = _get_message(message_id)
    if not message:
        return None

    html = None
    attachments = []
    inline_attachments = []
    for part in message.walk():
        if part.content_type.value == 'text/html' and not part.is_attachment():
            html = part.body
        elif part.is_attachment() or part.is_inline():
            attachment = Attachment(part)
            if part.is_inline():
                inline_attachments.append(attachment)
            else:
                attachments.append(attachment)

    # TODO split these up into separate tasks
    for attachment in attachments + inline_attachments:
        attachment.file = upload_attachment(attachment.mime, token)

    inline_attachment_dict = {}
    for attachment in inline_attachments:
        attachment_id = attachment.mime.headers.get('x-attachment-id')
        if attachment_id:
            inline_attachment_dict[attachment_id] = attachment

    # TODO should be handling empty subjects or bodies by notifying the user it
    # failed to parse
    if not html or not message.subject:
        if not message.subject:
            logger.error('message subject is required to create a post')
        else:
            logger.error('only plain text is supported currently')
        return None

    content = translate_html(html, inline_attachment_dict, attachments)
    state = post_containers.DRAFT if draft else post_containers.LISTED
    return post_containers.PostV1(
        title=message.subject,
        content=content,
        state=state,
        source=post_containers.EMAIL,
        source_id=message_id,
    )


def mark_message_as_processed(message_id):
    client = _get_boto_client('s3')
    unprocessed_key = _get_unprocessed_key(message_id)
    processed_key = _get_processed_key(message_id)
    try:
        response = client.copy_object(
            Bucket=settings.EMAIL_HOOK_S3_BUCKET,
            Key=processed_key,
            CopySource=os.path.join(settings.EMAIL_HOOK_S3_BUCKET, unprocessed_key),
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

    if (
        'ResponseMetadata' not in response or
        response['ResponseMetadata']['HTTPStatusCode'] != 204
    ):
        logger.exception('Unknown response: %s', response)
        raise ValueError('Unknown response: %s' % (response,))


def send_confirmation_to_user(post, user_email, domain):
    # XXX move this to the notification service
    client = _get_boto_client('ses', region_name=settings.EMAIL_SES_REGION)
    subject = 'Knowledge Published - %s' % (post.title,)
    post_url = get_post_resource_url(domain, post)
    root_url = get_root_url(domain)
    # XXX say "hey <persons name>"
    # XXX get their subdomain link
    message = (
        'Congrats! You\'ve completed Step 1 by using the handy create@ feature to publish '
        'knowledge from email. You can view and edit "%(title)s" on Luno here: %(resource_url)s.'
        '\n\nStep 2 is to scale yourself. The next time someone asks you about "%(title)s", '
        'don\'t waste energy finding and fowarding the email. Instead, politely refer them to '
        '%(root_url)s and tell them to search for it.\n\nCheers,\nLuno'
    ) % {
        'title': post.title,
        'resource_url': post_url,
        'root_url': root_url,
    }
    client.send_email(
        Source='"Luno"<%s>' % (settings.EMAIL_HOOK_NOTIFICATION_FROM_ADDRESS,),
        Destination={'ToAddresses': [user_email]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': message}},
        },
    )
