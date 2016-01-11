from file.models import File
from post.models import Attachment
from hooks.email.translators.trix import translate_html
from services.bootstrap import Bootstrap


def run():
    Bootstrap.bootstrap()

    attachments = Attachment.objects.all().select_related('post').order_by('post_id', 'created')
    files = File.objects.filter(pk__in=[a.file_id for a in attachments])
    file_dict = dict((f.id, f) for f in files)
    posts_dict = {}
    for attachment in attachments:
        attachment.file = file_dict[attachment.file_id].to_protobuf()
        posts_dict.setdefault(
            attachment.post_id,
            {'post': attachment.post, 'attachments': []},
        )['attachments'].append(attachment)

    for _, data in posts_dict.iteritems():
        post = data['post']
        attachments = data['attachments']
        content = post.content
        if not content.startswith('<div'):
            content = '<div>%s</div>' % (content,)

        inline_attachments = translate_html(content, {}, attachments)
        print '--- original post content: %s' % (post.id)
        print post.content.encode('utf-8')
        print '--- new post content: %s' % (post.id)
        print inline_attachments.encode('utf-8')
        print '---> %s deleting attachments: %s' % (post.id, str([(a.id, a.file_id) for a in attachments]))
        post.content = inline_attachments
        post.save()
        Attachment.objects.filter(pk__in=[a.id for a in attachments]).delete()
