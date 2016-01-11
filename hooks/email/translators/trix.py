import json
import math
import re

from lxml import html

from post.utils import (
    clean,
    ALLOWED_TAGS,
)

from .base import make_translator

SIZES = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB']


def format_size(size):
    """Format the size in bytes to a human readable value.

    Ported from: https://github.com/basecamp/trix/blob/8dad233e008cf0f1612db4a6bb7e303dce396ada/src/trix/config/file_size_formatting.coffee

    """
    if size == 0:
        return '0 Bytes'
    elif size == 1:
        return '1 Byte'

    exp = int(math.floor(math.log(size) / math.log(1024)))
    human_size = '%0.2f' % (size / math.pow(1024, exp),)
    without_insignificant_zeros = re.sub(r'\.$', '', re.sub(r'0*$', '', human_size))
    return '%s %s' % (without_insignificant_zeros, SIZES[exp])


def is_previewable(content_type):
    """Return whether or not we should specify the attachment as previewable.

    Ported from : https://github.com/basecamp/trix/blob/master/src/trix/models/attachment.coffee#L53

    """
    return re.match(r'^image(\/(gif|png|jpe?g)|$)', content_type)


def generate_trix_inline_attachment(f):
    """Generate an inline trix attachment from a file.

    Args:
        f (services.file.containers.FileV1): file to use as the source of the attachment

    """
    data_trix_attachment = {
        'contentType': f.content_type,
        'filename': f.name,
        'href': f.source_url,
        'url': f.source_url,
    }

    previewable = is_previewable(f.content_type)
    attachment_type = 'attachment-file'
    if previewable:
        attachment_type = 'attachment-preview'

    attachment = html.Element('a')
    attachment.set(
        'data-trix-attachment',
        json.dumps(data_trix_attachment, separators=(',', ':'), sort_keys=True),
    )
    attachment.set('data-trix-content-type', f.content_type)
    attachment.set('href', f.source_url)

    content_parts = f.content_type.split('/', 1)
    sub_content_type = content_parts[1] if len(content_parts) > 1 else ''
    figure = html.Element('figure')
    figure.set('class', 'attachment %s %s' % (attachment_type, sub_content_type))

    caption = html.Element('figcaption')
    caption.set('class', 'caption')
    caption.text = '%s ' % (f.name,)

    span = html.Element('span')
    span.text = format_size(f.size)
    caption.append(span)

    if previewable:
        image = html.Element('img')
        image.set('src', f.source_url)
        figure.append(image)

    figure.append(caption)

    attachment.append(figure)
    return attachment


def _translate_inline_image(element, attachments):
    if 'src' not in element.attrib:
        return

    source = element.attrib['src']
    if not source.startswith('cid:'):
        return

    _, content_id = source.split(':', 1)
    if content_id not in attachments:
        return

    attachment = attachments[content_id]
    trix_element = generate_trix_inline_attachment(attachment.file)

    element.addprevious(trix_element)

    parent = element.getparent()
    parent.remove(element)


def translate_element(element, attachments):
    if element.tag.endswith('img'):
        _translate_inline_image(element, attachments)


def translate_attachments(tree, attachments):
    for attachment in attachments:
        element = generate_trix_inline_attachment(attachment.file)
        tree.append(element)


def clean_html(html):
    """Clean the HTML after translations.

    Trix doesn't support nested div tags so in this process we strip out any
    divs along with any other invalid HTML, finally wrapping it in a single
    div.

    """
    tags = list(ALLOWED_TAGS)
    tags.remove('div')
    bleached = clean(html, strip=True, tags=tags)
    return '<div>%s</div>' % (bleached,)


translate_html = make_translator(translate_element, translate_attachments, clean_html)
