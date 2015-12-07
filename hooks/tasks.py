import service.control

from services.celery import app
from services.token import make_admin_token

from .email import actions


@app.task
def create_post_from_message(message_id, organization_id, by_profile_id, draft=False):
    post = actions.get_post_from_message(message_id, draft=draft)
    if not post:
        raise ValueError('invalid message_id')

    token = make_admin_token(
        organization_id=organization_id,
        profile_id=by_profile_id,
    )
    response = service.control.call_action(
        service='post',
        action='create_post',
        client_kwargs={'token': token},
        post=post,
    )

    actions.mark_message_as_processed(message_id)
    # TODO send an email to the user that the draft was created
