from elasticsearch.helpers import bulk
from elasticsearch_dsl import connections
import service.control

from services.celery import app
from services.token import make_admin_token

from .stores.es.types.profile.document import ProfileV1


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
    # TODO:
        # - should we be passing changed as version?
    documents = [ProfileV1.from_protobuf(profile) for profile in profiles]
    es = connections.connections.get_connection()
    bulk(es, documents)
