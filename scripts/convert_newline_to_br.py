"""Script to convert \n to <br>

https://www.wunderlist.com/#/tasks/1579839242

"""
import logging
import re

from post.models import Post
from services.bootstrap import Bootstrap

logger = logging.getLogger(__name__)


def run():
    Bootstrap.bootstrap()

    posts = Post.objects.all()
    update_count = 0
    for post in posts:
        content = post.content
        edited = False
        if not content.startswith('<div>'):
            logger.info('[post-%s] wrapping in div', post.id)
            content = '<div>%s</div>' % (content,)
            edited = True
        if '\n' in content:
            logger.info('[post-%s] replacing newlines with <br>', post.id)
            content = re.sub('\n', '<br>', content)
            edited = True

        if edited:
            logger.info(
                'updating post:%s\noriginal content:\n  >> %s\nnew content:\n  >> %s',
                post.id,
                post.content,
                content,
            )
            post.content = content
            post.save(update_fields=['content'])
            update_count += 1
    logger.info('cleanup complete, updated %d posts', update_count)
