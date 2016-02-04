import arrow
import re

from hooks.helpers import (
    get_profile_resource_url,
    get_post_resource_url,
)


def profile_to_slack_attachment(domain, profile):
    header = '%s (%s): %s' % (
        profile.full_name,
        profile.display_title,
        get_profile_resource_url(domain, profile),
    )
    return {
        'fallback': header,
        'pretext': header,
    }


def post_to_slack_attachment(domain, post, highlight):
    header = '<%s|%s> by <%s|%s>  |  %s' % (
        get_post_resource_url(domain, post),
        highlight_using_slack_formatting(highlight['title']) if 'title' in highlight else post.title,
        get_profile_resource_url(domain, post.by_profile),
        post.by_profile.full_name,
        arrow.get(post.created).format('MMMM D, YYYY')
    )
    text = '%s%s' % (
        highlight_using_slack_formatting(highlight['content']) if 'content' in highlight else post.snippet,
        '...' if len(post.snippet) >= 80 else '',
    )
    return {
        'fallback': header,
        'pretext': header,
        'text': text,
        'mrkdwn_in': ['pretext', 'text'],
    }


def result_to_slack_attachment(domain, result):
    result_type = result.WhichOneof('result_object')
    if result_type == 'profile':
        return profile_to_slack_attachment(domain, getattr(result, result_type))
    elif result_type == 'post':
        return post_to_slack_attachment(domain, getattr(result, result_type), result.highlight)


def highlight_using_slack_formatting(highlight):
    return re.sub('<[\/]?mark>', '*', highlight)
