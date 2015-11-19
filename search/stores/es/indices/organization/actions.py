import logging
import time

from elasticsearch_dsl import (
    connections,
    Index,
)
from . import INDEX_VERSION
from ... import types
from ...analysis import default_search

# XXX fix this
logger = logging.getLogger(__file__)


class DuplicateIndex(Exception):
    pass


def get_write_alias(organization_id):
    return '%s-write' % (organization_id,)


def get_read_alias(organization_id):
    return '%s-read' % (organization_id,)


def get_index_name(organization_id, version=None):
    version = version or INDEX_VERSION
    return '%s_v%s' % (organization_id, version)


def create_index(organization_id, version=None, check_duplicate=True):
    es = connections.connections.get_connection()
    write_alias = get_write_alias(organization_id)
    read_alias = get_read_alias(organization_id)
    if check_duplicate and es.indices.exists_alias('*', write_alias):
        aliases = es.indices.get_alias('*', organization_id)
        raise DuplicateIndex(aliases)

    index_name = get_index_name(organization_id, version=version)
    index = Index(index_name)

    aliases = {write_alias: {}}
    # we only create the read alias if one doesn't exist already. otherwise it
    # gets managed when migrating between indices
    if not es.indices.exists_alias('*', read_alias):
        aliases[read_alias] = {}

    index.aliases(**aliases)
    index.settings(index={'analysis': default_search.get_analysis_definition()})
    doc_types = ['LocationV1', 'PostV1', 'ProfileV1', 'TeamV1']
    for doc_type in doc_types:
        index.doc_type(getattr(types, doc_type))

    index.create()
    waiting = True
    while waiting:
        health = index.connection.cluster.health()
        waiting = health['status'] == 'red'
        # XXX switch to logger
        logger.info('waiting for cluster to get out of "red" status: %s' % (health,))
        time.sleep(1)
    return index
