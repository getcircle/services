import service.control

from services.celery import app
from services.token import make_admin_token

from .email import actions


@app.task
def create_post_from_message(
        message_id,
        organization_id,
        by_profile_id,
        ses_source,
        notify_email,
        draft=False,
    ):
    token = make_admin_token(
        organization_id=organization_id,
        profile_id=by_profile_id,
    )

    post = actions.get_post_from_message(message_id, token, draft=draft)
    if not post:
        raise ValueError('invalid message_id')

    response = service.control.call_action(
        service='post',
        action='create_post',
        client_kwargs={'token': token},
        post=post,
    )

    actions.mark_message_as_processed(message_id)
    actions.send_confirmation_to_user(response.result.post, ses_source, notify_email)
