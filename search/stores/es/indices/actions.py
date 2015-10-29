import contextlib

from elasticsearch_dsl import connections


@contextlib.contextmanager
def closed_index(index_name):
    connection = connections.connections.get_connection()
    connection.indices.close(index_name)
    yield
    connection.indices.open(index_name)
