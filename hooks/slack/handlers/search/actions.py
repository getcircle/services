from hooks.helpers import get_profile_resource_url


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
