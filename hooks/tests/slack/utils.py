from slacker import Response

from services.test import mocks


def mock_slack_user_info(patched, email='test@acme.com'):
    patched().users.info.return_value = Response(
        '{"ok": true, "user": {"profile": {"email": "%s"}}}' % (email,)
    )
    return email


def setup_mock_slack_test(mock, patched, organization):
    expected_email = mock_slack_user_info(patched)
    expected_profile = mocks.mock_profile(
        organization_id=organization.id,
        email=expected_email,
    )
    mock.instance.register_mock_object(
        service='profile',
        action='get_profile',
        return_object=expected_profile,
        return_object_path='profile',
        email=expected_email,
        inflations={'disabled': True},
    )
    return expected_profile
