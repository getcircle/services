from django.conf import settings


def if_es(func):
    """Helper to ensure we only run migration code if ES connection exists.

    The ES connection won't exist when running tests.

    """
    def _internal(*args, **kwargs):
        if settings.SEARCH_SERVICE_ELASTICSEARCH:
            return func(*args, **kwargs)
    return _internal
