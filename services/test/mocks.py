import arrow
from contextlib import contextmanager
import service.settings
from service.transports import local

from . import fuzzy
from .. import token

from protobufs.services.common.containers import description_pb2
from protobufs.services.file import containers_pb2 as file_containers
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.organization.containers import sso_pb2
from protobufs.services.organization.actions import get_teams_for_profile_ids_pb2
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search import containers_pb2 as search_containers
from protobufs.services.team import containers_pb2 as team_containers
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


def mock_team_deprecated(container=None, **overrides):
    if container is None:
        container = organization_containers.TeamV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'manager_profile_id', 'organization_id'],
        fuzzy.FuzzyText: ['name'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_user(container=None, **overrides):
    if container is None:
        container = user_containers.UserV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id'],
        fuzzy.FuzzyText(suffix='@exmaple.com'): ['primary_email'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_organization(container=None, **overrides):
    if container is None:
        container = organization_containers.OrganizationV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyText: ['name', 'domain'],
        fuzzy.FuzzyText(prefix='http://', suffix='.com'): ['image_url'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_profile(container=None, **overrides):
    if container is None:
        container = profile_containers.ProfileV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id', 'user_id', 'authentication_identifier'],
        fuzzy.FuzzyText: ['title', 'full_name', 'first_name', 'last_name', 'nickname'],
        fuzzy.FuzzyDate(arrow.Arrow(1980, 1, 1)): ['birth_date', 'hire_date'],
        fuzzy.FuzzyText(suffix='@example.com'): ['email'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_identity(container=None, **overrides):
    if container is None:
        container = user_containers.IdentityV1()

    defaults = {
        'provider': user_containers.IdentityV1.GOOGLE,
        'expires_at': str(arrow.utcnow().timestamp),
    }
    defaults.update(overrides)

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'access_token', 'provider_uid', 'user_id', 'organization_id'],
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


def mock_team(container=None, **overrides):
    if container is None:
        container = team_containers.TeamV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id'],
        fuzzy.FuzzyText: ['name'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_team_contact_method(container=None, **overrides):
    if container is None:
        container = team_containers.ContactMethodV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id'],
        fuzzy.FuzzyChoice(team_containers.ContactMethodV1.TypeV1.values()): ['type'],
        fuzzy.FuzzyText: ['label', 'value'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_organization_token(container=None, **overrides):
    if container is None:
        container = organization_containers.TokenV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['key', 'requested_by_user_id'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_device(container=None, **overrides):
    if container is None:
        container = user_containers.DeviceV1()

    defaults = {'provider': user_containers.DeviceV1.APPLE}
    defaults.update(overrides)

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'notification_token', 'device_uuid', 'user_id', 'organization_id'],
        fuzzy.FuzzyText: ['platform', 'os_version', 'app_version', 'language_preference'],
    }
    return _mock_container(container, mock_dict, **defaults)


def mock_description(container=None, **overrides):
    if container is None:
        container = description_pb2.DescriptionV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['by_profile_id'],
        fuzzy.FuzzyText: ['value'],
        fuzzy.FuzzyDate(arrow.utcnow()): ['changed'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_sso(container=None, **overrides):
    if container is None:
        container = sso_pb2.SSOV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['organization_id'],
    }

    defaults = {
        'saml': sso_pb2.SAMLDetailsV1(
            metadata_url=fuzzy.FuzzyText(suffix='.com', prefix='http://').fuzz(),
            metadata='<?xml version="1.0" encoding="UTF-8"?><md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="http://www.okta.com/exk509k1nntnbCg4B0h7"><md:IDPSSODescriptor WantAuthnRequestsSigned="true" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"><md:KeyDescriptor use="signing"><ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:X509Data><ds:X509Certificate>MIIDpDCCAoygAwIBAgIGAU+F5WdaMA0GCSqGSIb3DQEBBQUAMIGSMQswCQYDVQQGEwJVUzETMBEG\nA1UECAwKQ2FsaWZvcm5pYTEWMBQGA1UEBwwNU2FuIEZyYW5jaXNjbzENMAsGA1UECgwET2t0YTEU\nMBIGA1UECwwLU1NPUHJvdmlkZXIxEzARBgNVBAMMCmRldi00MTAzNjIxHDAaBgkqhkiG9w0BCQEW\nDWluZm9Ab2t0YS5jb20wHhcNMTUwODMxMjIzMzA4WhcNNDUwODMxMjIzNDA4WjCBkjELMAkGA1UE\nBhMCVVMxEzARBgNVBAgMCkNhbGlmb3JuaWExFjAUBgNVBAcMDVNhbiBGcmFuY2lzY28xDTALBgNV\nBAoMBE9rdGExFDASBgNVBAsMC1NTT1Byb3ZpZGVyMRMwEQYDVQQDDApkZXYtNDEwMzYyMRwwGgYJ\nKoZIhvcNAQkBFg1pbmZvQG9rdGEuY29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\ngeRZrc+svHeBVdVDsZX2lvvKLPPKWxWAWrGENqeQuXe8iomXgiyOHROf78eSke7nXUzdLFrjCUPP\na5m+LXTTDUEqfVIloZHiQZWq2hkp4JO0K3ksAdpNHcVeh9nKHOuHHznVvm+namP4PBRaz/yG43yN\n+Bl2XiyQjrSvG/6m7KmuLU1YL5IICeoYwU+r6WI4rCfoDoH+w7tgqyGBdqu38UiUc48/fWMqq1PW\n7tjS8B/ayFZnCdKclDPSCMoChtb95wbEgF2/w4PygYyb1GmjHxzjLGtxcSyvcyBC2w1CEHAq8ZWw\nRmyQ/2B6omz8EdXy92Q0rWIG/JYezOEki6FnjwIDAQABMA0GCSqGSIb3DQEBBQUAA4IBAQBzT+7o\nh1WvkLZ4P6LUS6CMntzgIJ7rB1JA85/kYc6pWu6Z8lIveG0Z4X1DXh4koVEcMXphzIUlXjduMFTG\nDn2i0nn0r4bcXhtKpyFUHqTPH6jhteQsjMnsi7vBzAstvWT2O14claCjxvG+YQN2ZSx4sX1dnZtU\nPdRdvkFD01680+WApwKOhlLf0vUd0s4TsM64QliN/WFwNeV3K5wAJ07XiDYVhoQ10QSPiG4DZEqb\n/CLouBrX5b0LxPMgQtdtOWM9eeRvNG8KCPZ4cPKLUh9kahI7g5xLDhQJhEfaKc+C5dcQ0HzoqXb+\nvlTMzJldSQEgQT5Lfikn7rL8ZuuZxLyD</ds:X509Certificate></ds:X509Data></ds:KeyInfo></md:KeyDescriptor><md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat><md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified</md:NameIDFormat><md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="https://dev-410362.oktapreview.com/app/rhlabsdev410362_lunolocal_2/exk509k1nntnbCg4B0h7/sso/saml"/><md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://dev-410362.oktapreview.com/app/rhlabsdev410362_lunolocal_2/exk509k1nntnbCg4B0h7/sso/saml"/></md:IDPSSODescriptor></md:EntityDescriptor>',
        ),
        'provider': sso_pb2.OKTA,
    }
    defaults.update(overrides)
    return _mock_container(container, mock_dict, **defaults)


def mock_saml_details(container=None, **overrides):
    if container is None:
        container = user_containers.SAMLDetailsV1()

    mock_dict = {
        fuzzy.FuzzyText: ['saml_response'],
    }
    defaults = {
        'domain': 'lunohq',
    }
    defaults.update(overrides)
    return _mock_container(container, mock_dict, **defaults)


def mock_profile_team(container=None, team_kwargs=None, **overrides):
    if container is None:
        container = get_teams_for_profile_ids_pb2.ResponseV1.ProfileTeamV1()

    if team_kwargs is None:
        team_kwargs = {}

    mock_dict = {
        fuzzy.FuzzyUUID: ['profile_id'],
    }
    defaults = {
        'team': mock_team_deprecated(**team_kwargs),
    }
    defaults.update(overrides)
    return _mock_container(container, mock_dict, **defaults)


def mock_post(container=None, **overrides):
    if container is None:
        container = post_containers.PostV1()

    mock_dict = {
        fuzzy.FuzzyText: ['title', 'content'],
        fuzzy.FuzzyUUID: ['organization_id', 'by_profile_id'],
        fuzzy.FuzzyDate(arrow.Arrow(1980, 1, 1)): ['created', 'changed'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_file(container=None, **overrides):
    if container is None:
        container = file_containers.FileV1()

    defaults = {
        'content_type': 'image/png',
    }

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'by_profile_id', 'organization_id'],
        fuzzy.FuzzyText(prefix='https://', suffix='.txt'): ['source_url'],
    }

    defaults.update(overrides)
    return _mock_container(container, mock_dict, **defaults)


def mock_search_result(container=None, **overrides):
    if container is None:
        container = search_containers.SearchResultV1()
    return _mock_container(container, {}, **overrides)


def mock_collection(container=None, **overrides):
    if container is None:
        container = post_containers.CollectionV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'organization_id', 'by_profile_id', 'owner_id'],
        fuzzy.FuzzyText: ['name'],
    }
    return _mock_container(container, mock_dict, **overrides)


def mock_collection_item(container=None, **overrides):
    if container is None:
        container = post_containers.CollectionItemV1()

    mock_dict = {
        fuzzy.FuzzyUUID: ['id', 'by_profile_id', 'source_id']
    }
    return _mock_container(container, mock_dict, **overrides)
