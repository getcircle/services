import arrow
from contextlib import contextmanager
import service.settings
from service.transports import local

from . import fuzzy
from .. import token

from protobufs.note_service_pb2 import NoteService
from protobufs.organization_service_pb2 import OrganizationService
from protobufs.profile_service_pb2 import ProfileService
from protobufs.resume_service_pb2 import ResumeService
from protobufs.user_service_pb2 import UserService


@contextmanager
def mock_transport(client):
    default_transport = service.settings.DEFAULT_TRANSPORT
    old_transport = client.transport
    try:
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        client.set_transport(local.instance)
        yield client
    finally:
        service.settings.DEFAULT_TRANSPORT = default_transport
        client.transport = old_transport


def _mock_container(container, mock_dict, **extra):
    # Support unsetting ids that we don't want set on the container
    clear_fields = []
    for key, value in extra.iteritems():
        if value is None:
            clear_fields.append(key)
    [extra.pop(key) for key in clear_fields]

    for mock_func, fields in mock_dict.iteritems():
        try:
            if issubclass(mock_func, fuzzy.BaseFuzzyAttribute):
                mock_func = mock_func().fuzz
        except TypeError:
            pass

        if hasattr(mock_func, 'fuzz') and not callable(mock_func):
            mock_func = mock_func.fuzz

        for field in fields:
            value = mock_func()
            if value and not isinstance(value, (bool, int)):
                value = str(value)
            setattr(container, field, value)

    for field, value in extra.iteritems():
        field_attribute = getattr(container, field)
        if isinstance(value, list) and hasattr(field_attribute, 'extend'):
            field_attribute.extend(value)
        elif hasattr(field_attribute, 'add'):
            if not hasattr(value, 'CopyFrom'):
                raise NotImplementedError('can only add protobuf to repeated fields')
            subcontainer = getattr(container, field).add()
            subcontainer.CopyFrom(value)
        elif hasattr(field_attribute, 'CopyFrom'):
            field_attribute.CopyFrom(value)
        else:
            setattr(container, field, value)

    for field in clear_fields:
        container.ClearField(field)
    return container


def mock_token(**values):
    mock_fields = ['auth_token', 'user_id', 'profile_id', 'organization_id']
    token_data = {}
    for field in mock_fields:
        token_data[field] = fuzzy.FuzzyUUID().fuzz()

    token_data.update(values)
    return token.make_token(**token_data)


def mock_address(container=None, **overrides):
    if container is None:
        container = OrganizationService.Containers.Address()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id'],
        fuzzy.FuzzyText: ['address_1', 'address_2', 'city', 'region'],
    }
    extra = {
        'postal_code': '94010',
        'country_code': 'US',
    }
    extra.update(overrides)
    return _mock_container(container, mock_dict, **extra)


def mock_team_path_part(container=None, **overrides):
    if container is None:
        container = OrganizationService.Containers.PathPart()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'owner_id'],
        fuzzy.FuzzyText: ['name'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_team(container=None, **overrides):
    if container is None:
        container = OrganizationService.Containers.Team()

    team_id = overrides.pop('id', fuzzy.FuzzyUUID().fuzz())
    mock_dict = {
        fuzzy.FuzzyUUID: ['owner_id', 'organization_id'],
        fuzzy.FuzzyText: ['name', 'department'],
    }
    path = overrides.pop('path', [])
    path.append(mock_team_path_part(id=team_id))
    extra = {
        'path': path,
        'id': team_id,
    }
    extra.update(overrides)
    return _mock_container(container, mock_dict, **extra)


def mock_organization(container=None, **overrides):
    if container is None:
        container = OrganizationService.Containers.Organization()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyText: ['name'],
        fuzzy.FuzzyText(prefix='.com'): ['domain'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_profile(container=None, **overrides):
    if container is None:
        container = ProfileService.Containers.Profile()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id', 'user_id', 'address_id', 'team_id'],
        fuzzy.FuzzyText: ['title', 'full_name', 'about'],
        fuzzy.FuzzyDate(arrow.Arrow(1980, 1, 1)): ['birth_date', 'hire_date'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_tag(container=None, **overrides):
    if container is None:
        container = ProfileService.Containers.Tag()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyText: ['name'],
        fuzzy.FuzzyChoice(ProfileService.TagType.values()): ['type'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_note(container=None, **overrides):
    if container is None:
        container = NoteService.Containers.Note()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'for_profile_id', 'owner_profile_id'],
        fuzzy.FuzzyText: ['content'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_identity(container=None, **overrides):
    if container is None:
        container = UserService.Containers.Identity()

    defaults = {
        'provider': UserService.LINKEDIN,
        'expires_at': str(arrow.utcnow().timestamp),
    }
    defaults.update(overrides)

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'access_token', 'provider_uid', 'user_id'],
        fuzzy.FuzzyText: ['full_name'],
        fuzzy.FuzzyText(suffix='@example.com'): ['email'],
    }
    return _mock_container(container, mock_dict, **defaults)


def mock_company(container=None, **overrides):
    if container is None:
        container = ResumeService.Containers.Company()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'linkedin_id'],
        fuzzy.FuzzyText: ['name'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_education(container=None, **overrides):
    if container is None:
        container = ResumeService.Containers.Education()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'user_id'],
        fuzzy.FuzzyText: ['school_name', 'notes', 'activities', 'degree', 'field_of_study'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_position(container=None, **overrides):
    if container is None:
        container = ResumeService.Containers.Position()

    defaults = {'company': mock_company()}
    defaults.update(overrides)

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'user_id'],
        fuzzy.FuzzyText: ['title', 'summary'],
    }
    return _mock_container(container, mock_dict, **defaults)


def mock_location(container=None, **overrides):
    if container is None:
        container = OrganizationService.Containers.Location()

    defaults = {'address': mock_address()}
    defaults.update(overrides)

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id'],
        fuzzy.FuzzyText: ['name'],
    }
    return _mock_container(container, mock_dict, **defaults)
