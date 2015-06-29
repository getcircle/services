import service.control

from profiles.models import Profile

from ..bootstrap import Bootstrap
from . import mocks


def setup_shell(service_name=None, profile=None):
    if profile is None:
        profile = Profile.objects.all()[0]

    Bootstrap.bootstrap()
    token = mocks.mock_token(
        profile_id=str(profile.id),
        organization_id=str(profile.organization_id),
    )
    if service_name:
        client = service.control.Client(service_name, token=token)
        return client
    return token
