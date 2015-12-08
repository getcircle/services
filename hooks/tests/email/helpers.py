import os

import mock

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
)


def mock_email_body(contents):
    body = mock.MagicMock()
    body.read.return_value = contents

    def _inner(*args, **kwargs):
        return {'Body': body}
    return _inner


def get_fixture_contents(fixture_name):
    with open(os.path.join(FIXTURE_PATH, fixture_name)) as read_file:
        return read_file.read()


def return_fixture(fixture_name, patched_boto):
    fixture = get_fixture_contents(fixture_name)
    return_contents(fixture, patched_boto)


def return_contents(contents, patched_boto):
    patched_boto.client().get_object.side_effect = mock_email_body(contents)
