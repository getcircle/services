import json

import html5lib

import service.control


def _delete_inline_attachments(content, token):
    """Trix stores attachments inline, when a post is deleted, we need to delete the files"""
    if 'data-trix-attachment' not in content:
        return

    file_ids = []
    tree = html5lib.parseFragment(content, treebuilder='lxml')[0]
    for element in tree.iter():
        if 'data-trix-attachment' in element.attrib:
            data = json.loads(element.attrib['data-trix-attachment'])
            if 'fileId' in data:
                file_ids.append(data['fileId'])

    if file_ids:
        service.control.call_action(
            service='file',
            action='delete',
            client_kwargs={'token': token},
            ids=file_ids,
        )


def delete_post(content, token):
    """Trix cleanup before deleting a post."""
    _delete_inline_attachments(content, token)
