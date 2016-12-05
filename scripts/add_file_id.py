import json

from bleach.encoding import force_unicode
import html5lib
from html5lib.serializer import serialize

from file.models import File
from post.models import Post

from services.bootstrap import Bootstrap


def ensure_file_id_present(post):
    tree = html5lib.parseFragment(post.content, treebuilder='lxml')[0]
    updated = False
    for element in tree.iter():
        if 'data-trix-attachment' in element.attrib:
            data_trix_attachment = json.loads(element.attrib['data-trix-attachment'])
            if 'fileId' not in data_trix_attachment:
                print 'adding fileId to post: %s' % (post.id,)
                f = File.objects.get_or_none(source_url=data_trix_attachment['href'])
                if not f:
                    print 'ERROR: couldn\'t lookup file with: %s' % (data_trix_attachment['href'],)
                    continue
                data_trix_attachment['fileId'] = str(f.id)
                element.set('data-trix-attachment', json.dumps(data_trix_attachment))
                updated = True

    if updated:
        print 'updating post: %s' % (post.id,)
        print 'original content:'
        print post.content.encode('utf-8')
        new_content = serialize(tree, tree='lxml', quote_attr_values=True).strip()
        post.content = force_unicode(new_content)
        print 'new content:'
        print post.content.encode('utf-8')
        post.save()


def run():
    Bootstrap.bootstrap()
    posts = Post.objects.all()
    for post in posts:
        if 'data-trix-attachment' in post.content:
            ensure_file_id_present(post)
