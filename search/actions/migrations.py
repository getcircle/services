from elasticsearch.helpers import reindex
from elasticsearch_dsl import connections

from ..stores.es.indices.organization import INDEX_VERSION
from ..stores.es.indices.organization.actions import (
    create_index,
    get_read_alias,
    get_write_alias,
)


def get_indices_to_migrate(current_version=INDEX_VERSION):
    es = connections.connections.get_connection()
    indices = es.cat.indices(h='index').split(' \n')
    is_old_index = lambda index: (
        len(index) > 3 and
        index[-2] == 'v' and
        not index.endswith(str(current_version))
    )
    return [index for index in indices if is_old_index(index)]


def migrate_index(index_name, current_version=INDEX_VERSION):
    organization_id, version = index_name.split('_')
    new_index = create_index(organization_id, version=current_version, check_duplicate=False)
    es = connections.connections.get_connection()
    reindex(es, source_index=index_name, target_index=new_index._name)
    # adjust the read and write aliases
    read_alias = get_read_alias(organization_id)
    write_alias = get_write_alias(organization_id)
    es.indices.update_aliases(body={
        'actions': [
            {'remove': {'index': index_name, 'alias': read_alias}},
            {'add': {'index': new_index._name, 'alias': read_alias}},
            {'remove': {'index': index_name, 'alias': write_alias}},
        ]
    })
    es.indices.delete(index_name)
    return new_index
