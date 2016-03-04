"""Script to convert trix attachment URLs so that they point to lunohq.com instead of S3, if they don't already."""
import json
import logging
import urllib
import urlparse

from bleach.encoding import force_unicode
from django.conf import settings
import html5lib
from html5lib.serializer import serialize

from post.models import Post
from organizations.models import Organization
from file.models import File
from services.bootstrap import Bootstrap

logger = logging.getLogger(__name__)


def translate_post(post):
    updated = False
    if 'data-trix-attachment' in post.content:
        tree = html5lib.parseFragment(force_unicode(post.content), treebuilder='lxml')[0]
        last_attachment_url = None
        last_attachment_new_url = None
        for element in tree.iter():
            if 'data-trix-attachment' in element.attrib:
                data = json.loads(element.attrib['data-trix-attachment'])
                url = data.get('url')
                if not url:
                    logger.info(
                        '[post-%s] "url" not found in data-trix-attachment',
                        post.id,
                    )
                    continue
                elif 'lunohq.com' in url:
                    continue

                organization = Organization.objects.get(
                    pk=post.organization_id,
                )
                file = File.objects.get(
                    pk=data['fileId']
                )
                last_attachment_url = url
                last_attachment_new_url = file._get_source_url(organization)
                data['href'] = last_attachment_new_url
                data['url'] = last_attachment_new_url
                element.attrib['data-trix-attachment'] = json.dumps(data)
                element.attrib['href'] = last_attachment_new_url
                element.attrib['target'] = '_blank'
                updated = True
            elif element.attrib.get('src', '') == last_attachment_url:
                element.attrib['src'] = last_attachment_new_url
                last_attachment_url = ''
                last_attachment_new_url = ''

        if updated:
            serialized = serialize(
                tree,
                tree='lxml',
                quote_attr_values=True,
                strip_whitespace=True,
            ).strip()
            logger.info(
                '[post-%s] updating post:\noriginal content:\n  >> %s\nnew content:\n  >> %s',
                post.id,
                post.content,
                serialized,
            )
            post.content = serialized
            post.save(update_fields=['content'])
    return updated


def run():
    Bootstrap.bootstrap()
    updated_count = 0
    for post in Post.objects.all():
        updated = translate_post(post)
        if updated:
            updated_count += 1
    logger.info('finished cleaning posts, updated %d posts', updated_count)
