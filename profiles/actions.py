import uuid

import arrow
from cacheops import cached_as
from django.core.exceptions import FieldError
import django.db
from django.db import connection
from django.db.models import (
    Count,
    Q,
)
from protobufs.services.profile import containers_pb2 as profile_containers
import service.control
from service import (
    actions,
    validators,
)

from services.token import parse_token
from services.utils import matching_uuids

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
        existing_profiles = models.Profile.objects.filter(
            email__in=[x.email for x in self.request.profiles]
        )
        existing_profiles_dict = dict((profile.email, profile) for profile in existing_profiles)
        containers_dict = dict((profile.email, profile) for profile in self.request.profiles)

        profiles_to_create = []
        for profile in self.request.profiles:
            if profile.email not in existing_profiles_dict:
                profiles_to_create.append(profile)

        profiles = self.bulk_create_profiles(profiles_to_create)
        contact_methods = []
        for profile in profiles:
            profile_container = containers_dict[profile.email]
            for container in profile_container.contact_methods:
                contact_method = models.ContactMethod.objects.from_protobuf(
                    container,
                    profile_id=profile.id,
                    commit=False,
                )
                contact_methods.append(contact_method)

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
        profile = models.Profile.objects.get(pk=self.request.profile.id)
        profile.update_from_protobuf(self.request.profile)
        profile.save()
        profile.to_protobuf(self.response.profile)


class GetProfile(actions.Action):
    # XXX add some concept of "oneof"

    type_validators = {
        'user_id': [validators.is_uuid4],
        'profile_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
        # TODO we should require organization_id here
        'user_id': {
            valid_profile_with_user_id: 'DOES_NOT_EXIST',
        },
    }

    def validate(self, *args, **kwargs):
        super(GetProfile, self).validate(*args, **kwargs)
        if not self.is_error():
            if not any([self.request.user_id, self.request.profile_id]):
                self.note_error(
                    'INVALID',
                    ('MISSING', '`user_id` or `profile_id` must be provided'),
                )

    def _get_profile(self):
        parameters = {}
        if self.request.profile_id:
            parameters['pk'] = self.request.profile_id
        else:
            parameters['user_id'] = self.request.user_id

        return models.Profile.objects.prefetch_related('contactmethod_set').get(**parameters)

    def run(self, *args, **kwargs):
        profile = self._get_profile()
        profile.to_protobuf(self.response.profile)


class GetProfiles(actions.Action):

    type_validators = {
        'team_id': [validators.is_uuid4],
        'organization_id': [validators.is_uuid4],
        'tag_id': [validators.is_uuid4],
        'address_id': [validators.is_uuid4],
        'ids': [validators.is_uuid4_list],
        'location_id': [validators.is_uuid4],
    }

    def validate(self, *args, **kwargs):
        super(GetProfiles, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.HasField('tag_id') and not self.request.HasField('organization_id'):
                raise self.ActionFieldError('organization_id', 'REQUIRED')

    def _populate_profiles_with_basic_keys(self):
        parameters = {}
        if self.request.tag_id:
            parameters['organization_id'] = self.request.organization_id
            parameters['tags__id'] = self.request.tag_id
        elif self.request.organization_id:
            parameters['organization_id'] = self.request.organization_id
        elif self.request.address_id:
            parameters['address_id'] = self.request.address_id
        elif self.request.ids:
            parameters['id__in'] = list(self.request.ids)
        elif self.request.location_id:
            parameters['location_id'] = self.request.location_id
        elif self.request.emails:
            parameters['email__in'] = list(self.request.emails)
        else:
            raise self.ActionError('missing parameters')

        profiles = models.Profile.objects.filter(**parameters).order_by(
            'first_name',
            'last_name',
        ).prefetch_related('contactmethod_set')
        self.paginated_response(
            self.response.profiles,
            profiles,
            lambda item, container: item.to_protobuf(container.add()),
        )

    def _populate_profiles_by_team_id(self):
        # fetch the team to get the owner
        client = service.control.Client('organization', token=self.token)
        response = client.call_action(
            'get_team',
            team_id=self.request.team_id,
            on_error=self.ActionFieldError('team_id', 'INVALID'),
        )
        team = response.result.team

        client = service.control.Client('profile', token=self.token)
        response = client.call_action(
            'get_direct_reports',
            user_id=team.owner_id,
            on_error=self.ActionError('ERROR_FETCHING_DIRECT_REPORTS'),
        )
        profiles = list(response.result.profiles)

        team_profiles = models.Profile.objects.filter(team_id=self.request.team_id).exclude(
            id__in=[profile.id for profile in profiles],
        ).prefetch_related('contactmethod_set')
        profiles.extend(team_profiles)
        profiles = sorted(profiles, key=lambda x: (x.first_name.lower(), x.last_name.lower()))
        for profile in profiles:
            container = self.response.profiles.add()
            if isinstance(profile, models.Profile):
                profile.to_protobuf(container)
            else:
                container.CopyFrom(profile)

    def run(self, *args, **kwargs):
        if self.request.team_id:
            self._populate_profiles_by_team_id()
        else:
            self._populate_profiles_with_basic_keys()


class GetExtendedProfile(GetProfile):

    def __init__(self, *args, **kwargs):
        super(GetExtendedProfile, self).__init__(*args, **kwargs)
        self.organization_client = service.control.Client('organization', token=self.token)

    def _fetch_location(self, location_id):
        # TODO this should raise an error if it doesn't succeed
        response = self.organization_client.call_action(
            'get_location',
            location_id=location_id,
        )
        return response.result.location

    def _fetch_team(self, team_id):
        # TODO this should raise an error if it doesn't succeed
        response = self.organization_client.call_action(
            'get_team',
            team_id=team_id,
        )
        return response.result.team

    def _get_manager(self, profile, team):
        user_id = team.owner_id
        if matching_uuids(team.owner_id, profile.user_id):
            try:
                manager_team = team.path[-2]
            except IndexError:
                return None

            response = self.organization_client.call_action(
                'get_team',
                team_id=manager_team.id,
                on_error=self.ActionError('ERROR_FETCHING_MANAGER_TEAM'),
            )
            user_id = response.result.team.owner_id
        return models.Profile.objects.prefetch_related('contactmethod_set').get(user_id=user_id)

    def _get_tags(self, tag_type):
        return models.Tag.objects.filter(
            profile=self.request.profile_id,
            type=tag_type,
        )

    def _get_skills(self):
        return self._get_tags(profile_containers.TagV1.SKILL)

    def _get_interests(self):
        return self._get_tags(profile_containers.TagV1.INTEREST)

    def _fetch_notes(self):
        # XXX error if we don't have profile_id?
        token = parse_token(self.token)
        client = service.control.Client('note', token=self.token)
        response = client.call_action(
            'get_notes',
            for_profile_id=self.request.profile_id,
            owner_profile_id=token.profile_id,
        )
        # XXX error if this doesn't succeed
        return response.result.notes

    def _fetch_direct_reports(self):
        client = service.control.Client('profile', token=self.token)
        response = client.call_action(
            'get_direct_reports',
            profile_id=self.request.profile_id,
        )
        return response.result.profiles

    def _fetch_identities(self, profile):
        client = service.control.Client('user', token=self.token)
        response = client.call_action(
            'get_identities',
            user_id=str(profile.user_id),
        )
        return response.result.identities

    def _fetch_resume(self, profile):
        client = service.control.Client('resume', token=self.token)
        response = client.call_action('get_resume', user_id=str(profile.user_id))
        return response.result.resume

    def run(self, *args, **kwargs):
        profile = self._get_profile()
        profile.to_protobuf(self.response.profile)

        location = self._fetch_location(str(profile.location_id))
        self.response.location.CopyFrom(location)

        team = self._fetch_team(str(profile.team_id))
        self.response.team.CopyFrom(team)

        direct_reports = self._fetch_direct_reports()
        self.response.direct_reports.extend(direct_reports)

        identities = self._fetch_identities(profile)
        self.response.identities.extend(identities)

        resume = self._fetch_resume(profile)
        self.response.resume.CopyFrom(resume)

        manager = self._get_manager(profile, team)
        if manager:
            manager.to_protobuf(self.response.manager)

        skills = self._get_skills()
        for skill in skills:
            container = self.response.skills.add()
            skill.to_protobuf(container)

        interests = self._get_interests()
        for interest in interests:
            container = self.response.interests.add()
            interest.to_protobuf(container)

        notes = self._fetch_notes()
        for note in notes:
            container = self.response.notes.add()
            container.CopyFrom(note)


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
    }

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.HasField('organization_id'):
            parameters['organization_id'] = self.request.organization_id
        else:
            parameters['profile'] = self.request.profile_id

        if self.request.HasField('tag_type'):
            parameters['type'] = self.request.tag_type

        tags = models.Tag.objects.filter(**parameters)
        for tag in tags:
            container = self.response.tags.add()
            tag.to_protobuf(container)


class GetDirectReports(actions.Action):

    type_validators = {
        'profile_id': [validators.is_uuid4],
        'user_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
    }

    def __init__(self, *args, **kwargs):
        super(GetDirectReports, self).__init__(*args, **kwargs)
        self.organization_client = service.control.Client('organization', token=self.token)

    def _get_child_team_owner_ids(self, team):
        response = self.organization_client.call_action(
            'get_team_descendants',
            team_ids=[team.id],
            on_error=self.ActionError('ERROR_FETCHING_TEAM_CHILDREN'),
            attributes=['owner_id'],
            depth=1,
        )
        descendants = response.result.descendants[0]
        return [item.owner_id for item in descendants.teams]

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.profile_id:
            parameters['pk'] = self.request.profile_id
        else:
            parameters['user_id'] = self.request.user_id

        try:
            profile = models.Profile.objects.get(**parameters)
        except models.Profile.DoesNotExist:
            raise self.ActionFieldError('user_id', 'DOES_NOT_EXIST')

        response = self.organization_client.call_action(
            'get_team',
            team_id=str(profile.team_id),
            on_error=self.ActionError('ERROR_FETCHING_TEAM'),
        )
        team = response.result.team
        user_ids = []
        if team.owner_id == str(profile.user_id):
            user_ids.extend(self._get_child_team_owner_ids(team))
            profiles = models.Profile.objects.filter(
                Q(user_id__in=user_ids) | Q(team_id=team.id),
                organization_id=profile.organization_id,
            ).exclude(pk=profile.id).extra(
                select={
                    'case_insensitive_first_name': 'lower(first_name)',
                    'case_insensitive_last_name': 'lower(last_name)',
                }
            ).order_by(
                'case_insensitive_first_name',
                'case_insensitive_last_name',
            ).prefetch_related('contactmethod_set')
            for profile in profiles:
                container = self.response.profiles.add()
                profile.to_protobuf(container)


class GetPeers(actions.Action):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        profile = models.Profile.objects.get(pk=self.request.profile_id)
        client = service.control.Client('organization', token=self.token)
        response = client.call_action(
            'get_team',
            team_id=str(profile.team_id),
            on_error=self.ActionError('ERROR_FETCHING_TEAM'),
        )
        team = response.result.team

        # handle CEO -- no peers
        if team.owner_id == str(profile.user_id) and len(team.path) < 2:
            return

        if team.owner_id == str(profile.user_id):
            client = service.control.Client('profile', token=self.token)
            response = client.call_action(
                'get_direct_reports',
                user_id=team.path[-2].owner_id,
                on_error=self.ActionError('ERROR_FETCHING_DIRECT_REPORTS'),
            )
            for item in response.result.profiles:
                if str(item.id) == str(profile.pk):
                    continue

                container = self.response.profiles.add()
                container.CopyFrom(item)
        else:
            profiles = models.Profile.objects.filter(team_id=profile.team_id).exclude(
                user_id=team.owner_id,
            ).exclude(pk=profile.id).extra(
                select={
                    'case_insensitive_first_name': 'lower(first_name)',
                    'case_insensitive_last_name': 'lower(last_name)',
                }
            ).order_by(
                'case_insensitive_first_name',
                'case_insensitive_last_name',
            ).prefetch_related('contactmethod_set')
            for item in profiles:
                if item.pk == profile.pk:
                    continue

                container = self.response.profiles.add()
                item.to_protobuf(container)


class GetProfileStats(actions.Action):

    type_validators = {
        'address_ids': [validators.is_uuid4_list],
        'location_ids': [validators.is_uuid4_list],
        'team_ids': [validators.is_uuid4_list],
    }

    def _get_profile_stats_for_address_ids(self, address_ids):
        stats = models.Profile.objects.filter(address_id__in=address_ids).values(
            'address_id',
        ).annotate(profiles=Count('id'))
        return dict((stat['address_id'], stat['profiles']) for stat in stats)

    def _get_profile_stats_for_location_ids(self, location_ids):
        stats = models.Profile.objects.filter(location_id__in=location_ids).values(
            'location_id',
        ).annotate(profiles=Count('id'))
        return dict((stat['location_id'], stat['profiles']) for stat in stats)

    def _get_profile_stats_for_team_ids(self, team_ids):
        stats = models.Profile.objects.filter(team_id__in=team_ids).values(
            'team_id',
        ).annotate(profiles=Count('id'))
        stats_dict = dict((stat['team_id'], stat['profiles']) for stat in stats)

        client = service.control.Client('organization', token=self.token)
        response = client.call_action(
            'get_team_descendants',
            team_ids=team_ids,
            attributes=['id'],
        )
        filter_ids = set()
        for descendants in response.result.descendants:
            filter_ids.update([item.id for item in descendants.teams])

        stats = models.Profile.objects.filter(
            team_id__in=filter_ids,
        ).values('team_id').annotate(profiles=Count('id'))
        for stat in stats:
            stats_dict[uuid.UUID(descendants.parent_team_id, version=4)] += stat['profiles']

        return stats_dict

    def run(self, *args, **kwargs):
        lookup_ids = []
        if self.request.address_ids:
            lookup_ids = self.request.address_ids
            stats_dict = self._get_profile_stats_for_address_ids(lookup_ids)
        elif self.request.location_ids:
            lookup_ids = self.request.location_ids
            stats_dict = self._get_profile_stats_for_location_ids(lookup_ids)
        elif self.request.team_ids:
            lookup_ids = self.request.team_ids
            stats_dict = self._get_profile_stats_for_team_ids(lookup_ids)
        else:
            raise self.ActionError(
                'FAILURE',
                ('FAILURE', 'Must specify filter parameter'),
            )

        for lookup_id in lookup_ids:
            # TODO type validators should check type and then transform to that
            # type so we're working with consistent values. ie. if we validate
            # uuid, we should have "uuid" type, not string
            lookup_id = uuid.UUID(lookup_id, version=4)
            container = self.response.stats.add()
            container.id = str(lookup_id)
            container.count = stats_dict.get(lookup_id, 0)


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
        ).prefetch_related('contactmethod_set')
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


class GetAttributesForProfiles(actions.Action):

    required_fields = ('attributes', 'location_id')
    type_validators = {
        'location_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            items = models.Profile.objects.filter(location_id=self.request.location_id).values(
                *self.request.attributes
            )
            if self.request.distinct:
                items = items.distinct(*self.request.attributes)
        except FieldError:
            raise self.ActionFieldError('attributes', 'INVALID')

        for item in items:
            for name in self.request.attributes:
                container = self.response.attributes.add()
                container.name = name
                container.value = str(item[name])
