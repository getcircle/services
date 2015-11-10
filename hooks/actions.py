import service.control
from slacker import Slacker


def get_email_for_slack_user(slack_api_token, user_id):
    slack = Slacker(slack_api_token)
    response = slack.users.info(user_id)
    return response.body['user']['profile']['email']


def get_profile_for_slack_user(token, slack_api_token, user_id):
    email = get_email_for_slack_user(slack_api_token, user_id)
    return service.control.get_object(
        service='profile',
        action='get_profile',
        return_object='profile',
        client_kwargs={'token': token},
        email=email,
        inflations={'enabled': False},
    )
