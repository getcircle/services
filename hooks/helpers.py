import urlparse

from django.conf import settings


def _get_resource_url(domain, path):
    parsed = urlparse.urlparse(settings.FRONTEND_URL)
    parsed = parsed._replace(netloc='%s.%s' % (domain, parsed.netloc))
    parsed = parsed._replace(path=path)
    return urlparse.urlunparse(parsed)


def get_profile_resource_url(domain, profile):
    path = 'profile/%s' % (profile.id,)
    return _get_resource_url(domain, path)


def get_post_resource_url(domain, post, edit=False):
    path = 'post/%s' % (post.id,)
    if edit:
        path += '/edit'
    return _get_resource_url(domain, path)


def get_root_url(domain):
    return _get_resource_url(domain, '/')
