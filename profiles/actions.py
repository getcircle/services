import arrow
from cacheops import cached_as
from common import utils
import django.db
from protobufs.services.search.containers import entity_pb2
import service.control
from service import (
    actions,
    validators,
)

from services.mixins import PreRunParseTokenMixin
from services.token import make_admin_token

from . import (
    models,
)


def valid_profile(profile_id):
    return models.Profile.objects.filter(pk=profile_id).exists()


def valid_profile_with_user_id(user_id):
    return models.Profile.objects.filter(user_id=user_id).exists()


def get_values_from_date_range(range_key, value_key, start, end):
    # cast to tuple so we can use it as input params to the db cursor
    return tuple(
        set([getattr(date, value_key) for date in arrow.Arrow.range(range_key, start, end)])
    )


class CreateProfile(actions.Action):

    type_validators = {
        'profile.address_id': [validators.is_uuid4],
        'profile.organization_id': [validators.is_uuid4],
        'profile.team_id': [validators.is_uuid4],
        'profile.user_id': [validators.is_uuid4],
    }

    def _create_profile(self):
        profile = None
        try:
            profile = models.Profile.objects.from_protobuf(
                self.request.profile,
            )
        except django.db.IntegrityError:
            self.note_error(
                'DUPLICATE',
                ('DUPLICATE', 'profile for user_id and organization_id already exists'),
            )
        return profile

    def run(self, *args, **kwargs):
        profile = self._create_profile()
        if profile:
            profile.to_protobuf(self.response.profile)


class BulkCreateProfiles(PreRunParseTokenMixin, actions.Action):

    def bulk_create_profiles(self, protobufs):
        objects = [models.Profile.objects.from_protobuf(
            profile,
            organization_id=self.parsed_token.organization_id,
            commit=False,
        ) for profile in protobufs]
        return models.Profile.objects.bulk_create(objects)

    def run(self, *args, **kwargs):
        existing_profiles = models.Profile.objects.filter(
            authentication_identifier__in=[
                x.authentication_identifier for x in self.request.profiles
            ],
            organization_id=self.parsed_token.organization_id,
        )
        existing_profiles_dict = dict((profile.authentication_identifier, profile) for profile
                                      in existing_profiles)
        containers_dict = dict((profile.authentication_identifier, profile) for profile
                               in self.request.profiles)

        profiles_to_create = []
        profiles_to_update = []
        for container in self.request.profiles:
            if container.authentication_identifier not in existing_profiles_dict:
                profiles_to_create.append(container)
            else:
                profile = existing_profiles_dict[container.authentication_identifier]
                if self.request.should_update:
                    profile.update_from_protobuf(container)
                profiles_to_update.append(profile)

        profiles = self.bulk_create_profiles(profiles_to_create)
        if profiles_to_update and self.request.should_update:
            models.Profile.bulk_manager.bulk_update(profiles_to_update)

        contact_methods = []
        for profile in profiles:
            profile_container = containers_dict[profile.authentication_identifier]
            for container in profile_container.contact_methods:
                contact_method = models.ContactMethod.objects.from_protobuf(
                    container,
                    profile_id=profile.id,
                    organization_id=profile.organization_id,
                    commit=False,
                )
                contact_methods.append(contact_method)

        profiles = profiles + profiles_to_update
        contact_methods = models.ContactMethod.objects.bulk_create(contact_methods)
        profile_id_to_contact_methods = {}
        for contact_method in contact_methods:
            profile_id_to_contact_methods.setdefault(contact_method.profile_id, []).append(
                contact_method,
            )

        profile_ids = []
        for profile in profiles:
            container = self.response.profiles.add()
            profile.to_protobuf(
                container,
                contact_methods=profile_id_to_contact_methods.get(profile.id),
            )
            profile_ids.append(str(profile.id))

        service.control.call_action(
            service='search',
            action='update_entities',
            client_kwargs={'token': self.token},
            ids=profile_ids,
            type=entity_pb2.PROFILE,
        )


class UpdateProfile(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'profile.id': [validators.is_uuid4],
        'profile.address_id': [validators.is_uuid4],
        'profile.organization_id': [validators.is_uuid4],
        'profile.team_id': [validators.is_uuid4],
        'profile.user_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile.id': {
            valid_profile: 'DOES_NOT_EXIST',
        }
    }

    def run(self, *args, **kwargs):
        # XXX add validation around by_profile_id. should only let admin and
        # the current user update the profile.
        profile = models.Profile.objects.get(
            pk=self.request.profile.id,
            organization_id=self.parsed_token.organization_id,
        )
        profile.update_from_protobuf(self.request.profile)
        profile.save()
        profile.to_protobuf(self.response.profile, token=self.token)


class GetProfile(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
        field = None
        if self.request.profile_id:
            parameters['pk'] = self.request.profile_id
            field = 'profile_id'
        elif self.request.email:
            parameters['email'] = self.request.email
            field = 'email'
        elif self.request.authentication_identifier:
            parameters['authentication_identifier'] = self.request.authentication_identifier
            field = 'authentication_identifier'
        else:
            # we might not have the organization_id right now
            parameters.pop('organization_id')
            parameters['user_id'] = self.parsed_token.user_id

        try:
            profile = models.Profile.objects.get(**parameters)
        except models.Profile.DoesNotExist:
            if field:
                raise self.ActionFieldError(field, 'DOES_NOT_EXIST')
            raise

        profile.to_protobuf(
            self.response.profile,
            inflations=self.request.inflations,
            token=self.token,
        )


class GetProfiles(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'ids': [validators.is_uuid4_list],
        'location_id': [validators.is_uuid4],
        'team_id': [validators.is_uuid4],
    }

    def _get_remote_profile_ids(self, return_object, **parameters):
        response = service.control.call_action(
            client_kwargs={'token': self.token},
            control={'paginator': self.control.paginator},
            **parameters
        )
        profile_ids = getattr(response.result, return_object)
        self.control.paginator.CopyFrom(response.control.paginator)
        return profile_ids

    def _get_parameters_from_remote_object(self):
        profile_ids = None
        if self.request.location_id:
            profile_ids = self._get_remote_profile_ids(
                'member_profile_ids',
                service='organization',
                action='get_location_members',
                location_id=self.request.location_id,
            )
        elif self.request.team_id:
            profile_ids = self._get_remote_profile_ids(
                'profile_ids',
                service='organization',
                action='get_descendants',
                team_id=self.request.team_id,
            )
        # XXX add tests for this
        elif self.request.manager_id:
            profile_ids = self._get_remote_profile_ids(
                'profile_ids',
                service='organization',
                action='get_descendants',
                profile_id=self.request.manager_id,
                direct=True,
            )
        return profile_ids

    def _get_profiles_teams(self, profiles):
        response = service.control.call_action(
            service='organization',
            action='get_teams_for_profile_ids',
            client_kwargs={'token': self.token},
            profile_ids=[p.id for p in profiles],
            fields={'only': ['name']},
        )
        return dict((p.profile_id, p.team) for p in response.result.profiles_teams)

    def _populate_display_title(self, container, profiles_teams):
        team = profiles_teams.get(container.id)
        if team and team.name:
            container.display_title = '%s (%s)' % (container.title, team.name)
        else:
            container.display_title = container.title

    def run(self, *args, **kwargs):
        parameters = {
            'organization_id': self.parsed_token.organization_id,
        }
        should_paginate = True
        if self.request.ids:
            parameters['id__in'] = list(self.request.ids)
        elif self.request.team_id or self.request.location_id:
            should_paginate = False
            profile_ids = self._get_parameters_from_remote_object()
            if not profile_ids:
                return
            parameters['id__in'] = profile_ids
        elif self.request.emails:
            parameters['email__in'] = self.request.emails
        elif self.request.is_admin:
            parameters['is_admin'] = True
        elif self.request.authentication_identifiers:
            parameters['authentication_identifier__in'] = self.request.authentication_identifiers

        profiles = models.Profile.objects.filter(**parameters).order_by(
            'first_name',
            'last_name',
        )
        if utils.should_inflate_field('contact_methods', self.request.inflations):
            profiles = profiles.prefetch_related('contact_methods')

        # remote calls have already been paginated, we don't want to overwrite their pagination
        if should_paginate:
            self.paginated_response(
                self.response.profiles,
                profiles,
                lambda item, container: item.to_protobuf(
                    container.add(),
                    inflations=self.request.inflations,
                    display_title=None,
                ),
            )
        else:
            for profile in profiles:
                profile.to_protobuf(
                    self.response.profiles.add(),
                    inflations=self.request.inflations,
                    display_title=None,
                )

        if utils.should_inflate_field('display_title', self.request.inflations):
            profiles_teams = self._get_profiles_teams(self.response.profiles)
            for profile in self.response.profiles:
                self._populate_display_title(profile, profiles_teams)


class GetExtendedProfile(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'profile_id': (validators.is_uuid4,),
    }
    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
    }

    def _export_profiles_list(self, profile_ids, response_container, profile_dict):
        for profile_id in profile_ids:
            container = response_container.add()
            profile = profile_dict.get(profile_id)
            if profile:
                profile.to_protobuf(container, contact_methods=None, token=self.token)

    def _populate_reporting_details(self, client):
        response = client.call_action(
            'get_profile_reporting_details',
            profile_id=self._get_profile_id(),
        )
        reporting_details = response.result
        profile_ids = []
        for container in (
            reporting_details.peers_profile_ids,
            reporting_details.direct_reports_profile_ids,
        ):
            profile_ids.extend(container)

        if reporting_details.manager_profile_id:
            profile_ids.append(reporting_details.manager_profile_id)

        if profile_ids:
            profiles = models.Profile.objects.filter(
                id__in=profile_ids,
                organization_id=self.parsed_token.organization_id,
            )
            profile_dict = dict((str(profile.id), profile) for profile in profiles)
            self._export_profiles_list(
                reporting_details.peers_profile_ids,
                self.response.peers,
                profile_dict,
            )
            self._export_profiles_list(
                reporting_details.direct_reports_profile_ids,
                self.response.direct_reports,
                profile_dict,
            )
            manager = profile_dict.get(reporting_details.manager_profile_id)
            if manager:
                manager.to_protobuf(
                    self.response.manager,
                    contact_methods=None,
                    token=self.token,
                )

        if reporting_details.team.ByteSize():
            self.response.team.CopyFrom(reporting_details.team)
        if reporting_details.manages_team.ByteSize():
            self.response.manages_team.CopyFrom(reporting_details.manages_team)

    def _populate_locations(self, client):
        locations = client.get_object(
            'get_locations',
            return_object='locations',
            profile_id=self._get_profile_id(),
            inflations={'only': ['profile_count']},
        )
        self.response.locations.extend(locations)

    def _get_profile_id(self):
        return self.request.profile_id or self.parsed_token.profile_id

    def run(self, *args, **kwargs):
        profile = models.Profile.objects.prefetch_related('contact_methods').get(
            organization_id=self.parsed_token.organization_id,
            pk=self._get_profile_id(),
        )
        profile.to_protobuf(self.response.profile, token=self.token)

        identities = service.control.get_object(
            'user',
            'get_identities',
            client_kwargs={'token': self.token},
            return_object='identities',
            user_id=str(profile.user_id),
        )
        self.response.identities.extend(identities)

        organization_client = service.control.Client('organization', token=self.token)
        self._populate_reporting_details(organization_client)
        self._populate_locations(organization_client)


class GetUpcomingAnniversaries(actions.Action):

    required_fields = ('organization_id',)
    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def _get_parameters_list(self):
        now = arrow.utcnow()
        return [
            get_values_from_date_range('day', 'day', now, now.replace(days=7)),
            get_values_from_date_range('day', 'month', now, now.replace(days=7)),
            now.date(),
            self.request.organization_id,
        ]

    def _build_anniversaries_query(self):
        return (
            'SELECT * FROM %s WHERE'
            ' EXTRACT(day from hire_date) in %%s'
            ' AND EXTRACT(month from hire_date) in %%s'
            ' AND hire_date < %%s'
            ' AND organization_id = %%s'
            ' ORDER BY EXTRACT(month from hire_date), EXTRACT(day from hire_date)'
        ) % (models.Profile._meta.db_table,)

    def run(self, *args, **kwargs):

        @cached_as(models.Profile.objects.filter(organization_id=self.request.organization_id))
        def _get_profiles():
            return list(models.Profile.objects.raw(
                self._build_anniversaries_query(),
                self._get_parameters_list(),
            ))

        for profile in _get_profiles():
            container = self.response.profiles.add()
            profile.to_protobuf(container)


class GetUpcomingBirthdays(actions.Action):

    required_fields = ('organization_id',)
    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def _get_parameters_list(self):
        now = arrow.utcnow()
        return [
            get_values_from_date_range('day', 'day', now, now.replace(days=7)),
            get_values_from_date_range('day', 'month', now, now.replace(days=7)),
            self.request.organization_id,
        ]

    def _build_birthdays_query(self):
        return (
            'SELECT * FROM %s WHERE'
            ' EXTRACT(day from birth_date) in %%s'
            ' AND EXTRACT(month from birth_date) in %%s'
            ' AND organization_id = %%s'
            ' ORDER BY birth_date'
        ) % (models.Profile._meta.db_table,)

    def run(self, *args, **kwargs):

        @cached_as(models.Profile.objects.filter(organization_id=self.request.organization_id))
        def _get_profiles():
            return list(models.Profile.objects.raw(
                self._build_birthdays_query(),
                self._get_parameters_list(),
            ))

        for profile in _get_profiles():
            container = self.response.profiles.add()
            profile.to_protobuf(container)


class ProfileExists(actions.Action):

    required_fields = ('domain',)

    def validate(self, *args, **kwargs):
        super(ProfileExists, self).validate(*args, **kwargs)
        if not self.is_error():
            if not (self.request.email or self.request.authentication_identifier):
                raise self.ActionError(
                    'MISSING_ARGUMENTS',
                    ('MISSING_ARGUMENTS', 'email or authentication_identifier required'),
                )

    def run(self, *args, **kwargs):
        try:
            organization = service.control.get_object(
                service='organization',
                action='get_organization',
                client_kwargs={'token': make_admin_token()},
                return_object='organization',
                domain=self.request.domain,
            )
        except service.control.CallActionError:
            raise self.ActionFieldError('domain', 'DOES_NOT_EXIST')

        parameters = {'organization_id': organization.id}
        if self.request.email:
            parameters['email'] = self.request.email
        else:
            parameters['authentication_identifier'] = self.request.authentication_identifier

        profile = models.Profile.objects.get_or_none(**parameters)
        self.response.organization_id = organization.id
        if not profile:
            self.response.exists = False
        else:
            self.response.exists = True
            self.response.user_id = str(profile.user_id)
            self.response.profile_id = str(profile.id)
