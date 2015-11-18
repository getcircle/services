import time

from elasticsearch_dsl import (
    connections,
    Index,
)
from . import INDEX_VERSION
from ...analysis import default_search

# XXX
# - fetch all the organization_ids in our system
# - create a _vN index for them
# - migrate over the last index
# - at any time we only have 1 previous version in the system.
# - we almost then don't need to have this prefixed as "_v1", since its not
# going to be different, we just want to bump the number. if the current index
# is already loaded, we're going to migrate anyways, it doesn't help to have
# the history stored in separate directories (git has the history)

# this becomes search/stores/es/indices/organization/actions.py


class DuplicateIndex(Exception):
    pass


def get_current_index_name(organization_id):
    return '%s_v%s' % (organization_id, INDEX_VERSION)


def create_index(organization_id):
    es = connections.connections.get_connection()
    if es.indices.exists_alias('*', organization_id):
        aliases = es.indices.get_alias('*', organization_id)
        raise DuplicateIndex(aliases)

    index_name = get_current_index_name(organization_id)
    index = Index(index_name)
    index.aliases(**{organization_id: {}})
    index.settings(index={'analysis': default_search.get_analysis_definition()})
    index.create()
    waiting = True
    while waiting:
        health = index.connection.cluster.health()
        waiting = health['status'] == 'red'
        # XXX switch to logger
        print 'waiting for cluster to get out of "red" status: %s' % (health,)
        time.sleep(1)
