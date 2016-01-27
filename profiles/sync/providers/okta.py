import json
import logging
import time

import arrow
from protobufs.services.profile import containers_pb2 as profile_containers
import requests
import service.control

from profiles.models import Profile
from services.token import make_admin_token

from .. import utils

logger = logging.getLogger(__name__)


class ProviderMappings(object):

    fields = (
        'authentication_identifier',
        'title',
        'first_name',
        'last_name',
        'hire_date',
        'email',
        'manager_authentication_identifier',
        'source_id',
        'location',
        'department',
    )

    def __init__(self, **kwargs):
        for field in self.fields:
            if field in kwargs:
                value = kwargs[field]
            else:
                value = None
            setattr(self, field, value)


class RequestError(Exception):

    def __init__(self, response):
        self.response = response
        message = self._build_message_from_response(response)
        super(RequestError, self).__init__(message)

    def _build_message_from_response(self, response):
        return 'Requesting url: "%s" failed with: [Status: %s] [Reason: %s]' % (
            response.request.url,
            response.status_code,
            response.reason,
        )


class RequiredFieldMissingError(Exception):

    def __init__(self, field, user):
        self.field = field
        self.user = user
        message = 'Required field missing: "%s"' % (field,)
        super(RequiredFieldMissingError, self).__init__(message)


class InvalidFieldTypeError(Exception):

    def __init__(self, field_type):
        self.field_type = field_type
        message = 'Field type not found in whitelist: "%s"' % (field_type,)
        super(InvalidFieldTypeError, self).__init__(message)


class FieldValueInvalidTypeError(Exception):

    def __init__(self, value, field_type):
        self.value = value
        self.field_type = field_type
        message = 'Invalid field value: "%s" (%s) - expected type: %s' % (
            value,
            type(value),
            field_type,
        )
        super(FieldValueInvalidTypeError, self).__init__(message)


class FieldValueInvalidError(Exception):

    def __init__(self, value, allowed_values):
        self.value = value
        self.allowed_values = allowed_values
        message = 'Invalid field value: "%s" - expected one of: %s' % (
            value,
            allowed_values,
        )
        super(FieldValueInvalidError, self).__init__(message)


def _safe_eval(value):
    allowed_field_types = [
        'str',
        'int',
        '_date',
    ]
    if value not in allowed_field_types:
        raise InvalidFieldTypeError(value)
    return eval(value)


def _make_authorization_header(api_key):
    return 'SSWS %s' % (api_key,)


def _fetch_all_users(url, api_key):
    """Recursively fetch all users from Okta.

    Args:
        url (str): the Okta URL endpoint for the organization, ie.
            https://${org}.okta.com/api/v1/users
        api_key: an Okta API key that has access to pull users

    Returns:
        list: a list of Okta user models
            (http://developer.okta.com/docs/api/resources/users.html#user-model)

    """
    users = []

    authorization_header = _make_authorization_header(api_key)
    response = requests.get(url, headers={'Authorization': authorization_header})
    if not response.ok:
        raise RequestError(response)

    for user in response.json():
        users.append(user)

    if response.links.get('next'):
        users.extend(_fetch_all_users(response.links['next']['url'], api_key))
    return users


def _validate_user(user, validate_fields):
    for field, requirements in validate_fields.iteritems():
        try:
            value = utils.get_path_from_dict(field, user)
        except KeyError:
            value = None

        if value is None and requirements.get('required'):
            raise RequiredFieldMissingError(field, user)

        field_type = requirements.get('type')
        if field_type:
            try:
                value = _safe_eval(field_type)(value)
            except ValueError:
                raise FieldValueInvalidTypeError(value, field_type)

        allowed_values = requirements.get('values')
        if allowed_values and value not in allowed_values:
            raise FieldValueInvalidError(value, allowed_values)

        utils.set_path_in_dict(field, value, user)


def _date(value):
    return arrow.get(value).format('YYYY-MM-DD')


def _get_profile_from_user(user, rules):
    profile = {}
    mappings = rules['mappings']
    validate_fields = rules.get('validate_fields')
    if validate_fields:
        _validate_user(user, validate_fields)

    for field in mappings.fields:
        path = getattr(mappings, field)
        if path:
            try:
                profile[field] = utils.get_path_from_dict(path, user)
            except KeyError:
                continue

    return profile


def _get_profiles(users, rules):
    profiles = []
    invalid_users = 0
    for user in users:
        try:
            profile = _get_profile_from_user(user, rules)
        except (
            RequiredFieldMissingError,
            InvalidFieldTypeError,
            FieldValueInvalidError,
            FieldValueInvalidTypeError,
        ):
            invalid_users += 1
            continue
        else:
            profiles.append(profile)
    logger.info('%d out of %d users invalid', invalid_users, len(users))
    return profiles


def _create_profile(provider_profile, organization_id, commit=True):
    token = make_admin_token(organization_id=organization_id)
    user_id = ''
    if commit:
        user = service.control.get_object(
            service='user',
            action='create_user',
            client_kwargs={'token': token},
            return_object='user',
            email=provider_profile['email'],
            organization_id=str(organization_id),
        )
        user_id = user.id

    items = []
    for key in ['Department', 'Location']:
        value = provider_profile.get(key.lower())
        if value:
            item = (key, provider_profile[key.lower()])
            items.append(item)

    protobuf = profile_containers.ProfileV1(
        title=provider_profile.get('title') or '',
        first_name=provider_profile['first_name'],
        last_name=provider_profile['last_name'],
        hire_date=provider_profile.get('hire_date') or '',
        authentication_identifier=provider_profile['authentication_identifier'],
        organization_id=str(organization_id),
        user_id=user_id,
    )
    profile = Profile.objects.from_protobuf(
        protobuf,
        sync_source_id=provider_profile['source_id'],
        commit=commit,
        items=items,
    )
    return profile


def _sync_profile(provider_profile, profile, commit=True):
    fields_to_sync = [
        'first_name',
        'last_name',
        'authentication_identifier',
        'title',
        'hire_date',
        'email',
    ]
    logger.info('syncing profile: %s', profile.id)
    for field in fields_to_sync:
        provider_value = provider_profile.get(field)
        if provider_value:
            if field == 'hire_date':
                provider_value = arrow.get(provider_value).date()

            profile_value = getattr(profile, field)
            if profile_value != provider_value:
                logger.info(
                    'updating %s - new value (%s), original value (%s)',
                    field,
                    provider_value,
                    profile_value,
                )
                setattr(profile, field, provider_value)

    items_to_sync = ['Department', 'Location']
    items = []
    for item in profile.items or []:
        if item[0] in items_to_sync:
            value = provider_profile.get(item[0].lower())
            if value:
                current = [item[0], value]
                if current != item:
                    logger.info(
                        'updating %s - new value (%s), original value (%s)',
                        item[0],
                        current,
                        item,
                    )
                    item = current
            items_to_sync.remove(item[0])
        items.append(item)

    for key in items_to_sync:
        value = provider_profile.get(key.lower())
        if value:
            item = (key, value)
            logger.info('adding %s item', item)
            items.append(item)

    profile.items = items
    if profile.status == profile_containers.ProfileV1.INACTIVE:
        _activate_profile(profile, commit=commit)

    profile.sync_source_id = provider_profile['source_id']
    if commit:
        profile.save()
    return profile


def _activate_profile(profile, commit=True):
    logger.info('activating profile: %s', profile.id)
    if not commit:
        return

    profile.status = profile_containers.ProfileV1.ACTIVE
    token = make_admin_token(organization_id=profile.organization_id)
    service.control.call_action(
        service='user',
        action='bulk_update_users',
        client_kwargs={'token': token},
        users=[{'id': str(profile.user_id), 'is_active': True}],
    )


def _deactivate_profile(profile, commit=True):
    logger.info('deactivating profile: %s', profile.id)
    if not commit:
        return

    token = make_admin_token(organization_id=profile.organization_id)
    service.control.call_action(
        service='user',
        action='bulk_update_users',
        client_kwargs={'token': token},
        users=[{'id': str(profile.user_id), 'is_active': False}],
    )

    profile.status = profile_containers.ProfileV1.INACTIVE
    profile.save()


def _set_manager(profile_id, manager_profile_id, token, commit=True):
    if not commit:
        logger.info('would set manager for: %s to %s', profile_id, manager_profile_id)
        return

    service.control.call_action(
        service='organization',
        action='set_manager',
        client_kwargs={'token': token},
        manager_profile_id=manager_profile_id,
        profile_id=profile_id,
    )


def _sync_users(users, rules, organization_id, commit=True):
    provider_profiles = _get_profiles(users, rules)
    logger.info('%d valid provider profiles', len(provider_profiles))
    existing_profiles = Profile.objects.filter(organization_id=organization_id)
    identifier_to_profile = dict((p.authentication_identifier, p) for p in existing_profiles)
    token = make_admin_token(organization_id=organization_id)

    profiles = []
    synced_profiles = 0
    new_profiles = 0

    for provider_profile in provider_profiles:
        luno_profile = identifier_to_profile.get(provider_profile['authentication_identifier'])
        if not luno_profile:
            new_profiles += 1
            profile = _create_profile(provider_profile, organization_id, commit=commit)
        else:
            synced_profiles += 1
            profile = _sync_profile(provider_profile, luno_profile, commit=commit)
        provider_profile['_id'] = profile.id
        profiles.append(profile)

    # loop through provider_profiles after we know we've populated all profiles
    # to account for managers that weren't in the system yet
    identifier_to_profile = dict((p.authentication_identifier, p) for p in profiles)
    for provider_profile in provider_profiles:
        manager_id = provider_profile.get('manager_authentication_identifier')
        if manager_id:
            manager_profile = identifier_to_profile.get(manager_id)
            if manager_profile:
                _set_manager(
                    str(provider_profile['_id']),
                    str(manager_profile.id),
                    token,
                    commit=commit,
                )

    provider_identifiers = [p['authentication_identifier'] for p in provider_profiles]
    deactivated_profiles = 0
    for profile in existing_profiles:
        if profile.authentication_identifier not in provider_identifiers:
            deactivated_profiles += 1
            _deactivate_profile(profile, commit=commit)

    logger.info(
        'synced %d profiles, created %d profiles, deactivated %d profiles',
        synced_profiles,
        new_profiles,
        deactivated_profiles,
    )


def sync(settings, commit=True):
    """Sync details from the Okta API to our system.

    Args:
        settings (profiles.models.SyncSettings): Sync settings for the organization

    """
    rules = {
        'validate_fields': json.loads(settings.validate_fields),
        'mappings': ProviderMappings(**json.loads(settings.mappings)),
    }

    start = time.time()
    logger.info(
        'starting sync: %s\nvalidate_fields: %s\nmappings: %s',
        settings.endpoint,
        settings.validate_fields,
        settings.mappings,
    )
    users = _fetch_all_users(settings.endpoint, settings.api_key)
    logger.info('fetched: %d users', len(users))
    _sync_users(users, rules, settings.organization_id, commit=commit)
    end = time.time()
    logger.info('sync complete: %s seconds', (end - start))
