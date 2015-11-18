from elasticsearch.helpers import bulk
from elasticsearch_dsl import connections
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.search.containers import entity_pb2
import service.control

from services.celery import app
from services.token import make_admin_token

from .stores.es.types.location.document import LocationV1
from .stores.es.types.post.document import PostV1
from .stores.es.types.profile.document import ProfileV1
from .stores.es.types.team.document import TeamV1


def _update_documents(document_type, protobufs):
    # TODO:
        # - should we be passing changed as version?
    documents = [document_type.from_protobuf(protobuf).to_dict(include_meta=True) for protobuf
                 in protobufs]
    es = connections.connections.get_connection()
    bulk(es, documents)


@app.task
def update_profiles(ids, organization_id):
    profiles = service.control.get_object(
        service='profile',
        action='get_profiles',
        return_object='profiles',
        client_kwargs={'token': make_admin_token(organization_id=organization_id)},
        control={'paginator': {'page_size': len(ids)}},
        ids=ids,
        inflations={'only': ['display_title']},
    )
    _update_documents(ProfileV1, profiles)


@app.task
def update_teams(ids, organization_id):
    teams = service.control.get_object(
        service='organization',
        action='get_teams',
        return_object='teams',
        client_kwargs={'token': make_admin_token(organization_id=organization_id)},
        control={'paginator': {'page_size': len(ids)}},
        ids=ids,
    )
    _update_documents(TeamV1, teams)


@app.task
def update_locations(ids, organization_id):
    locations = service.control.get_object(
        service='organization',
        action='get_locations',
        return_object='locations',
        client_kwargs={'token': make_admin_token(organization_id=organization_id)},
        control={'paginator': {'page_size': len(ids)}},
        ids=ids,
    )
    _update_documents(LocationV1, locations)


@app.task
def update_posts(ids, organization_id):
    posts = service.control.get_object(
        service='post',
        action='get_posts',
        return_object='posts',
        client_kwargs={'token': make_admin_token(organization_id=organization_id)},
        control={'paginator': {'page_size': len(ids)}},
        ids=ids,
        state=post_containers.LISTED,
    )
    _update_documents(PostV1, posts)


@app.task
def delete_entities(ids, entity_type, organization_id):

    _build_action = lambda document_id, document_type: {
        '_id': document_id,
        '_op_type': 'delete',
        '_index': document_type._doc_type.index,
        '_type': document_type._doc_type.name,
    }

    document_type = None
    if entity_type == entity_pb2.PROFILE:
        document_type = ProfileV1
    elif entity_type == entity_pb2.TEAM:
        document_type = TeamV1
    elif entity_type == entity_pb2.LOCATION:
        document_type = LocationV1
    elif entity_type == entity_pb2.POST:
        document_type = PostV1

    actions = [_build_action(_id, document_type) for _id in ids]
    es = connections.connections.get_connection()
    bulk(es, actions)
