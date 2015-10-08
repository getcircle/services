from django.contrib.auth.hashers import make_password

import service.control

DEFAULT_PASSWORD = make_password('rhlabs')


def add_users(emails, token, password=None):
    users = [{'primary_email': email, 'password': password or DEFAULT_PASSWORD}
             for email in emails]
    client = service.control.Client('user', token=token)
    response = client.call_action('bulk_create_users', users=users)
    return response.result.users
