import service.control

from protobuf_to_dict import protobuf_to_dict
from services.celery import app
from services.token import make_admin_token

from .stores.es.types.profile.document import ProfileV1


@app.task
def update_profile(primary_key, organization_id):
    profile = service.control.get_object(
        service='profile',
        action='get_profile',
        return_object='profile',
        client_kwargs={'token': make_admin_token(organization_id=organization_id)},
        profile_id=primary_key,
        inflations={'only': ['display_title']},
    )
    # TODO:
        # - should we be passing changed as version?
        # - do we need to check if the doc exists?
    document = ProfileV1(_id=profile.id, **protobuf_to_dict(profile))
    document.save()
