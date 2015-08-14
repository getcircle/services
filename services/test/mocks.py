import arrow
from contextlib import contextmanager
import service.settings
from service.transports import local

from . import fuzzy
from .. import token

from protobufs.services.common import containers_pb2 as common_containers
from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.user import containers_pb2 as user_containers
from protobufs.services.user.containers import token_pb2


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
    mock_fields = ['auth_token', 'auth_token_id', 'user_id', 'profile_id', 'organization_id']
    token_data = {}
    for field in mock_fields:
        token_data[field] = fuzzy.FuzzyUUID().fuzz()
    token_data['client_type'] = token_pb2.IOS

    token_data.update(values)
    return token.make_token(**token_data)


def mock_team(container=None, **overrides):
    if container is None:
        container = organization_containers.TeamV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'manager_profile_id', 'organization_id'],
        fuzzy.FuzzyText: ['name'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_organization(container=None, **overrides):
    if container is None:
        container = organization_containers.OrganizationV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyText: ['name'],
        fuzzy.FuzzyText(suffix='.com'): ['domain'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_profile(container=None, **overrides):
    if container is None:
        container = profile_containers.ProfileV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id', 'user_id'],
        fuzzy.FuzzyText: ['title', 'full_name', 'first_name', 'last_name', 'nickname'],
        fuzzy.FuzzyDate(arrow.Arrow(1980, 1, 1)): ['birth_date', 'hire_date'],
        fuzzy.FuzzyText(suffix='@example.com'): ['email'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_tag(container=None, **overrides):
    if container is None:
        container = profile_containers.TagV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyText: ['name'],
        fuzzy.FuzzyChoice(profile_containers.TagV1.TagTypeV1.values()): ['tag_type'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_identity(container=None, **overrides):
    if container is None:
        container = user_containers.IdentityV1()

    defaults = {
        'provider': user_containers.IdentityV1.LINKEDIN,
        'expires_at': str(arrow.utcnow().timestamp),
    }
    defaults.update(overrides)

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'access_token', 'provider_uid', 'user_id'],
        fuzzy.FuzzyText: ['full_name'],
        fuzzy.FuzzyText(suffix='@example.com'): ['email'],
    }
    return _mock_container(container, mock_dict, **defaults)


def mock_location(container=None, **overrides):
    if container is None:
        container = organization_containers.LocationV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id'],
        fuzzy.FuzzyText: ['name', 'address_1', 'address_2', 'city', 'region'],
    }
    defaults = {
        'postal_code': '94010',
        'country_code': 'US',
    }
    defaults.update(overrides)
    return _mock_container(container, mock_dict, **defaults)


def mock_contact_method(container=None, **overrides):
    if container is None:
        container = profile_containers.ContactMethodV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyChoice(profile_containers.ContactMethodV1.ContactMethodTypeV1.values()): [
            'contact_method_type'
        ],
        fuzzy.FuzzyText: ['label', 'value'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_group(container=None, **overrides):
    if container is None:
        container = group_containers.GroupV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyText: ['name', 'display_name', 'group_description'],
        fuzzy.FuzzyText(suffix='@circlehq.co'): ['email'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_member(container=None, profile_overrides=None, should_mock_profile=True, **overrides):
    if container is None:
        container = group_containers.MemberV1()

    if profile_overrides is None:
        profile_overrides = {}

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyChoice(group_containers.RoleV1.values()): ['role'],
    }
    container = _mock_container(container, mock_dict, **overrides)
    if should_mock_profile:
        container.profile.CopyFrom(mock_profile(**profile_overrides))
    return container


def mock_organization_token(container=None, **overrides):
    if container is None:
        container = organization_containers.TokenV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['key', 'requested_by_user_id'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_group_membership_request(container=None, **overrides):
    if container is None:
        container = group_containers.MembershipRequestV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'requester_profile_id', 'group_id'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_device(container=None, **overrides):
    if container is None:
        container = user_containers.DeviceV1()

    defaults = {'provider': user_containers.DeviceV1.APPLE}
    defaults.update(overrides)

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'notification_token', 'device_uuid', 'user_id'],
        fuzzy.FuzzyText: ['platform', 'os_version', 'app_version', 'language_preference'],
    }
    return _mock_container(container, mock_dict, **defaults)


def mock_description(container=None, **overrides):
    if container is None:
        container = common_containers.DescriptionV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['by_profile_id'],
        fuzzy.FuzzyText: ['value'],
        fuzzy.FuzzyDate(arrow.utcnow()): ['changed'],
    }
    return _mock_container(container, mock_dict, **overrides)
