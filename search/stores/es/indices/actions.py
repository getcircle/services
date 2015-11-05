import contextlib

from django.conf import settings
from elasticsearch_dsl import connections


@contextlib.contextmanager
def closed_index(index_name):
    # AWS ES Service doesn't support close/open index at the moment
    is_aws_es = settings.SEARCH_SERVICE_ELASTICSEARCH_URL.endswith('es.amazonaws.com')
    if not is_aws_es:
        connection = connections.connections.get_connection()
        connection.indices.close(index_name)
    yield
    if not is_aws_es:
        connection.indices.open(index_name)
