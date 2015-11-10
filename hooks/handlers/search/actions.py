import urlparse

from django.conf import settings


def _get_resource_url(path):
    parsed = urlparse.urlparse(settings.FRONTEND_URL)
    parsed = parsed._replace(path=path)
    return urlparse.urlunparse(parsed)


def get_profile_resource_url(profile):
    path = 'profile/%s' % (profile.id,)
    return _get_resource_url(path)


def profile_to_slack_attachment(profile):
    header = '%s (%s): %s' % (
        profile.full_name,
        profile.display_title,
        get_profile_resource_url(profile),
    )
    return {
        'fallback': header,
        'pretext': header,
    }


def result_to_slack_attachment(result):
    result_type = result.WhichOneof('result_object')
    if result_type == 'profile':
        return profile_to_slack_attachment(getattr(result, result_type))
