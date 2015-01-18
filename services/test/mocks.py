from . import fuzzy

from protobufs.organization_service_pb2 import OrganizationService
from protobufs.profile_service_pb2 import ProfileService


def _mock_container(container, mock_dict, **extra):
    for mock_func, fields in mock_dict.iteritems():
        try:
            if issubclass(mock_func, fuzzy.BaseFuzzyAttribute):
                mock_func = mock_func().fuzz
        except TypeError:
            pass

        for field in fields:
            setattr(container, field, mock_func())

    for field, value in extra.iteritems():
        field_attribute = getattr(container, field)
        if isinstance(value, list) and hasattr(field_attribute, 'extend'):
            field_attribute.extend(value)
        elif hasattr(field_attribute, 'add'):
            if not hasattr(value, 'CopyFrom'):
                raise NotImplementedError('can only add protobuf to repeated fields')
            subcontainer = getattr(container, field).add()
            subcontainer.CopyFrom(value)
        else:
            setattr(container, field, value)
    return container


def mock_address(container=None, **overrides):
    if container is None:
        container = OrganizationService.Containers.Address()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyText: ['address_1', 'address_2', 'city', 'region'],
    }
    extra = {
        'postal_code': '94010',
        'country_code': 'US',
    }
    extra.update(overrides)
    return _mock_container(container, mock_dict, **extra)


def mock_team_path_parth(container=None, **overrides):
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

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'owner_id', 'organization_id'],
        fuzzy.FuzzyText: ['name', 'department'],
    }
    extra = {
        'path': [mock_team_path_parth()],
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
        fuzzy.FuzzyUUID: ['id', 'organization_id'],
        fuzzy.FuzzyText: ['title', 'full_name'],
    }
    return _mock_container(container, mock_dict, **overrides)
