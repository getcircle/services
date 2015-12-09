import urlparse

from django.conf import settings


def _get_resource_url(path):
    parsed = urlparse.urlparse(settings.FRONTEND_URL)
    parsed = parsed._replace(path=path)
    return urlparse.urlunparse(parsed)


def get_profile_resource_url(profile):
    path = 'profile/%s' % (profile.id,)
    return _get_resource_url(path)


def get_post_resource_url(post):
    path = 'post/%s' % (post.id,)
    return _get_resource_url(path)
