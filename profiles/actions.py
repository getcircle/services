import arrow
from cacheops import cached_as
import django.db
from django.db import connection
import service.control
from service import (
    actions,
    validators,
)

from services.mixins import PreRunParseTokenMixin
from services.token import make_admin_token
from services.utils import should_inflate_field

from . import (
    models,
)


def valid_profile(profile_id):
    return models.Profile.objects.filter(pk=profile_id).exists()


def valid_profile_with_user_id(user_id):
    return models.Profile.objects.filter(user_id=user_id).exists()


def valid_tag(tag):
    return tag.HasField('name') and tag.HasField('tag_type')


def valid_tag_list(tag_list):
    return all(map(valid_tag, tag_list))


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


class BulkCreateProfiles(actions.Action):

    @classmethod
    def bulk_create_profiles(cls, protobufs):
        objects = [models.Profile.objects.from_protobuf(
            profile,
            commit=False,
        ) for profile in protobufs]
        return models.Profile.objects.bulk_create(objects)

    def run(self, *args, **kwargs):
        # TODO this should have organization id
        existing_profiles = models.Profile.objects.filter(
            email__in=[x.email for x in self.request.profiles]
        )
        existing_profiles_dict = dict((profile.email, profile) for profile in existing_profiles)
        containers_dict = dict((profile.email, profile) for profile in self.request.profiles)

        profiles_to_create = []
        profiles_to_update = []
        for container in self.request.profiles:
            if container.email not in existing_profiles_dict:
                profiles_to_create.append(container)
            else:
                profile = existing_profiles_dict[container.email]
                profile.update_from_protobuf(container)
                profiles_to_update.append(profile)

        profiles = self.bulk_create_profiles(profiles_to_create)
        if profiles_to_update:
            models.Profile.bulk_manager.bulk_update(profiles_to_update)

        contact_methods = []
        for profile in profiles:
            profile_container = containers_dict[profile.email]
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

        for profile in profiles:
            container = self.response.profiles.add()
            profile.to_protobuf(
                container,
                contact_methods=profile_id_to_contact_methods.get(profile.id),
            )


class UpdateProfile(actions.Action):

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
        profile = models.Profile.objects.get(
            pk=self.request.profile.id,
        )
        profile.update_from_protobuf(self.request.profile)
        profile.save()
        profile.to_protobuf(self.response.profile)


class GetProfile(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.profile_id:
            parameters['pk'] = self.request.profile_id
            parameters['organization_id'] = self.parsed_token.organization_id,
        else:
            parameters['user_id'] = self.parsed_token.user_id

        profile = models.Profile.objects.get(**parameters)
        profile.to_protobuf(
            self.response.profile,
            inflations=self.request.inflations,
            token=self.token,
        )


class GetProfiles(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'tag_id': [validators.is_uuid4],
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
                action_name='get_location_members',
                location_id=self.request.location_id,
            )
        elif self.request.team_id:
            profile_ids = self._get_remote_profile_ids(
                'profile_ids',
                service='organization',
                action_name='get_descendants',
                team_id=self.request.team_id,
            )
        # XXX add tests for this
        elif self.request.manager_id:
            profile_ids = self._get_remote_profile_ids(
                'profile_ids',
                service='organization',
                action_name='get_descendants',
                profile_id=self.request.manager_id,
                direct=True,
            )
        return profile_ids

    def _get_profiles_teams(self, profiles):
        response = service.control.call_action(
            service='organization',
            action_name='get_teams_for_profile_ids',
            client_kwargs={'token': self.token},
            profile_ids=[p.id for p in profiles],
            fields={'only': ['name']},
        )
        return dict((p.profile_id, p.team) for p in response.result.profiles_teams)

    def _populate_display_title(self, container, profiles_teams):
        team = profiles_teams.get(container.id)
        if team:
            container.display_title = '%s (%s)' % (container.title, team.name)

    def run(self, *args, **kwargs):
        parameters = {
            'organization_id': self.parsed_token.organization_id,
        }
        should_paginate = True
        if self.request.tag_id:
            parameters['tags__id'] = self.request.tag_id
        elif self.request.ids:
            parameters['id__in'] = list(self.request.ids)
        elif self.request.team_id or self.request.location_id:
            should_paginate = False
            profile_ids = self._get_parameters_from_remote_object()
            if not profile_ids:
                return
            parameters['id__in'] = profile_ids

        profiles = models.Profile.objects.filter(**parameters).order_by(
            'first_name',
            'last_name',
        )
        if should_inflate_field('contact_methods', self.request.inflations):
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
                profile.to_protobuf(container, contact_methods=None, status=None, token=self.token)

    def _populate_reporting_details(self, client):
        response = client.call_action(
            'get_profile_reporting_details',
            profile_id=self.request.profile_id,
        )
        reporting_details = response.result
        profile_ids = []
        for container in (
            reporting_details.peers_profile_ids,
            reporting_details.direct_reports_profile_ids,
        ):
            profile_ids.extend(container)

        if reporting_details.HasField('manager_profile_id'):
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
                manager.to_protobuf(self.response.manager, contact_methods=None, status=None)

        if reporting_details.HasField('team'):
            self.response.team.CopyFrom(reporting_details.team)
        if reporting_details.HasField('manages_team'):
            self.response.manages_team.CopyFrom(reporting_details.manages_team)

    def _populate_locations(self, client):
        locations = client.get_object(
            'get_locations',
            return_object='locations',
            profile_id=self.request.profile_id,
            inflations={'only': ['profile_count']},
        )
        self.response.locations.extend(locations)

    def run(self, *args, **kwargs):
        profile = models.Profile.objects.prefetch_related('contact_methods').get(
            pk=self.request.profile_id,
            organization_id=self.parsed_token.organization_id,
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


class CreateTags(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
        'tags': [valid_tag_list],
    }

    def _create_tags(self, organization_id, tags):
        # dedupe the tags
        tags = dict((tag.name, tag) for tag in tags).values()
        objects = [models.Tag.objects.from_protobuf(
            tag,
            commit=False,
            organization_id=organization_id,
        ) for tag in tags]
        models.Tag.objects.bulk_create(objects)
        return models.Tag.objects.filter(
            name__in=[tag.name for tag in tags],
            organization_id=organization_id,
        )

    def run(self, *args, **kwargs):
        tags = self._create_tags(self.request.organization_id, self.request.tags)
        for tag in tags:
            container = self.response.tags.add()
            tag.to_protobuf(container)


class AddTags(CreateTags):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
    }

    def _dedupe_tags(self, tag_ids):
        # NOTE: this is subject to a race condition, but since we only have 1
        # interface to add tags we're not going to worry about this for now.
        through_model = models.Profile.tags.through
        current_tag_ids = map(str, through_model.objects.filter(
            profile_id=self.request.profile_id,
        ).values_list('tag_id', flat=True))
        return list(set(tag_ids) - set(current_tag_ids))

    def _add_tags(self, tags):
        tag_ids = [tag.id for tag in tags]
        deduped_tag_ids = self._dedupe_tags(tag_ids)
        through_model = models.Profile.tags.through
        objects = [through_model(
            profile_id=self.request.profile_id,
            tag_id=tag_id,
        ) for tag_id in deduped_tag_ids]
        return through_model.objects.bulk_create(objects)

    def run(self, *args, **kwargs):
        tags_to_create = [tag for tag in self.request.tags if not tag.id]
        tags_to_add = [tag for tag in self.request.tags if tag.id]
        if tags_to_create:
            organization_id = models.Profile.objects.get(
                pk=self.request.profile_id
            ).organization_id
            tags_to_add.extend(self._create_tags(organization_id, tags_to_create))

        if tags_to_add:
            self._add_tags(tags_to_add)


class RemoveTags(actions.Action):

    required_fields = ('profile_id', 'tags')

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        models.ProfileTags.objects.filter(
            profile_id=self.request.profile_id,
            tag_id__in=set([tag.id for tag in self.request.tags]),
        ).delete()


class GetTags(actions.Action):

    # XXX should we have field_validators for whether or not organization and profile exist?

    type_validators = {
        'organization_id': [validators.is_uuid4],
        'profile_id': [validators.is_uuid4],
        'ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.HasField('organization_id'):
            parameters['organization_id'] = self.request.organization_id
        elif self.request.ids:
            # XXX add organization filter
            parameters['id__in'] = self.request.ids
        else:
            parameters['profile'] = self.request.profile_id

        if self.request.HasField('tag_type'):
            parameters['type'] = self.request.tag_type

        tags = models.Tag.objects.filter(**parameters)
        for tag in tags:
            container = self.response.tags.add()
            tag.to_protobuf(container)


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


class GetRecentHires(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        now = arrow.utcnow()
        # XXX sort by hire_date
        profiles = models.Profile.objects.filter(
            organization_id=self.request.organization_id,
            hire_date__gte=now.replace(days=-7).date,
        ).prefetch_related('contact_methods')
        for profile in profiles:
            container = self.response.profiles.add()
            profile.to_protobuf(container)


class GetActiveTags(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def _get_main_query(self):
        tag_type_condition = ''
        if self.request.HasField('tag_type'):
            tag_type_condition = 'AND "%s"."type" = %%s' % (models.Tag._meta.db_table,)
        return (
            '"%(profiles_tag)s" where "%(profiles_tag)s"."id" in ('
            'SELECT DISTINCT id FROM ('
            'SELECT "%(profiles_tag)s"."id" FROM "%(profiles_tag)s" INNER JOIN '
            '"%(profiles_profiletags)s" ON ('
            '"%(profiles_tag)s"."id" = "%(profiles_profiletags)s"."tag_id")'
            ' WHERE ("%(profiles_profiletags)s"."tag_id" IS NOT NULL '
            'AND "%(profiles_tag)s"."organization_id" = %%s) %(tag_type_condition)s ORDER BY'
            ' "%(profiles_profiletags)s"."created" DESC) as nested_query)'
        ) % {
            'profiles_tag': models.Tag._meta.db_table,
            'profiles_profiletags': models.ProfileTags._meta.db_table,
            'tag_type_condition': tag_type_condition,
        }

    def _build_count_query(self):
        return 'SELECT COUNT(*) FROM %s' % (self._get_main_query(),)

    def _build_tags_query(self, offset, limit):
        return 'SELECT * FROM %s OFFSET %s LIMIT %s' % (self._get_main_query(), offset, limit)

    def _get_count(self, params):
        cursor = connection.cursor()
        cursor.execute(self._build_count_query(), params)
        return cursor.fetchone()[0]

    def run(self, *args, **kwargs):
        main_params = [self.request.organization_id]
        cache_queryset = models.ProfileTags.objects.filter(
            tag__organization_id=self.request.organization_id
        )
        if self.request.HasField('tag_type'):
            main_params.append(self.request.tag_type)
            cache_queryset = cache_queryset.filter(tag__type=self.request.tag_type)

        @cached_as(cache_queryset)
        def _get_count_block():
            return self._get_count(main_params)

        count = _get_count_block()
        offset, limit = self.get_pagination_offset_and_limit(count)

        @cached_as(cache_queryset, extra='%s.%s' % (offset, limit))
        def _get_tags_block():
            # NB: Cast the raw queryset to a list so that it doesn't raise a
            # TypeError within paginated_response since RawQuerySet has no length
            # attribute
            return list(models.Tag.objects.raw(self._build_tags_query(offset, limit), main_params))

        self.paginated_response(
            self.response.tags,
            _get_tags_block(),
            lambda item, container: item.to_protobuf(container.add()),
            count=count,
        )


class ProfileExists(actions.Action):

    required_fields = ('email', 'domain')

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
            raise self.ActionFieldError('domain')

        self.response.exists = models.Profile.objects.filter(
            email=self.request.email,
            organization_id=organization.id,
        ).exists()
