import os


def _get_delimited_setting_from_environment(key, default):
    value = os.environ.get(key)
    if isinstance(value, basestring):
        value = value.split(',')
    return value or default
