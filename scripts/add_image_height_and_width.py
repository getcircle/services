"""Script to add height and width to trix attachments that don't have it already.

https://www.wunderlist.com/#/tasks/1580124462

"""
import json
import logging
import urllib
import urlparse

from bleach.encoding import force_unicode
import boto3
from django.conf import settings
import html5lib
from html5lib.serializer import serialize
# NOTE: requires us to install PIL in the container before running this
# $ apt-get install -y python-dev libjpeg-dev libfreetype6-dev zlib1g-dev
# $ pip install pillow
from PIL import Image

from post.models import Post
from services.bootstrap import Bootstrap

logger = logging.getLogger(__name__)


def get_s3_bucket_and_key(url):
    parsed_url = urlparse.urlparse(url)
    bucket_name = parsed_url.hostname.split('.', 1)[0]
    key_name = urllib.unquote(parsed_url.path[1:])
    return bucket_name, key_name


def translate_post(s3, post):
    updated = False
    if 'data-trix-attachment' in post.content:
        tree = html5lib.parseFragment(force_unicode(post.content), treebuilder='lxml')[0]
        last_image_url = None
        last_height = None
        last_width = None
        for element in tree.iter():
            if (
                'data-trix-attachment' in element.attrib and
                element.attrib.get('data-trix-content-type', '').startswith('image')
            ):
                data = json.loads(element.attrib['data-trix-attachment'])
                url = data.get('url')
                if not url:
                    logger.info(
                        '[post-%s] "url" not found in data-trix-attachment',
                        post.id,
                    )
                    continue

                bucket, key = get_s3_bucket_and_key(url)
                obj = s3.Object(bucket, key)
                response = obj.get()
                image = Image.open(response['Body'])
                last_image_url = data['url']
                last_width, last_height = image.size
                data['height'] = last_height
                data['width'] = last_width
                element.attrib['data-trix-attachment'] = json.dumps(data)
            elif element.attrib.get('src', '') == last_image_url:
                element.attrib['height'] = str(last_height)
                element.attrib['width'] = str(last_width)
                last_image_url = None
                last_height = None
                last_width = None

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
        updated = True
    return updated


def run():
    Bootstrap.bootstrap()
    s3 = boto3.resource(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    updated_count = 0
    for post in Post.objects.all():
        updated = translate_post(s3, post)
        if updated:
            updated_count += 1
    logger.info('finished cleaning posts, updated %d posts', updated_count)
