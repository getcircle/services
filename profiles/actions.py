import uuid

import arrow
import django.db
from django.db.models import (
    Count,
    Q,
)
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

        return models.Profile.objects.get(**parameters)

    def run(self, *args, **kwargs):
        profile = self._get_profile()
        profile.to_protobuf(self.response.profile)


class GetProfiles(actions.Action):

    type_validators = {
        'team_id': [validators.is_uuid4],
        'organization_id': [validators.is_uuid4],
        'skill_id': [validators.is_uuid4],
        'address_id': [validators.is_uuid4],
        'ids': [validators.is_uuid4_list],
    }

    def _get_profiles_with_basic_keys(self):
        parameters = {}
        if self.request.organization_id:
            parameters['organization_id'] = self.request.organization_id
        elif self.request.address_id:
            parameters['address_id'] = self.request.address_id
        elif self.request.ids:
            parameters['id__in'] = list(self.request.ids)
        else:
            parameters['skills__id'] = self.request.skill_id

        return models.Profile.objects.filter(**parameters).order_by('first_name', 'last_name')

    def _get_profiles_by_team_id(self):
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
        )
        profiles.extend(team_profiles)
        return sorted(profiles, key=lambda x: (x.first_name, x.last_name))

    def run(self, *args, **kwargs):
        if self.request.team_id:
            profiles = self._get_profiles_by_team_id()
        else:
            profiles = self._get_profiles_with_basic_keys()

        for profile in profiles:
            container = self.response.profiles.add()
            if isinstance(profile, models.Profile):
                profile.to_protobuf(container)
            else:
                container.CopyFrom(profile)


class GetExtendedProfile(GetProfile):

    def __init__(self, *args, **kwargs):
        super(GetExtendedProfile, self).__init__(*args, **kwargs)
        self.organization_client = service.control.Client('organization', token=self.token)

    def _fetch_address(self, address_id):
        # TODO this should raise an error if it doesn't succeed
        response = self.organization_client.call_action(
            'get_address',
            address_id=address_id,
        )
        return response.result.address

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
        return models.Profile.objects.get(user_id=user_id)

    def _get_skills(self):
        return models.Skill.objects.filter(profile=self.request.profile_id)

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

    def run(self, *args, **kwargs):
        profile = self._get_profile()
        profile.to_protobuf(self.response.profile)

        address = self._fetch_address(str(profile.address_id))
        self.response.address.CopyFrom(address)

        team = self._fetch_team(str(profile.team_id))
        self.response.team.CopyFrom(team)

        direct_reports = self._fetch_direct_reports()
        self.response.direct_reports.extend(direct_reports)

        identities = self._fetch_identities(profile)
        self.response.identities.extend(identities)

        manager = self._get_manager(profile, team)
        if manager:
            manager.to_protobuf(self.response.manager)

        skills = self._get_skills()
        for skill in skills:
            container = self.response.skills.add()
            skill.to_protobuf(container)

        notes = self._fetch_notes()
        for note in notes:
            container = self.response.notes.add()
            container.CopyFrom(note)


class CreateSkills(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def _create_skills(self, organization_id, skills):
        # dedupe the skills
        skills = dict((skill.name, skill) for skill in skills).values()
        objects = [models.Skill.objects.from_protobuf(
            skill,
            commit=False,
            organization_id=organization_id,
        ) for skill in skills]
        models.Skill.objects.bulk_create(objects)
        return models.Skill.objects.filter(name__in=[skill.name for skill in skills])

    def run(self, *args, **kwargs):
        skills = self._create_skills(self.request.organization_id, self.request.skills)
        for skill in skills:
            container = self.response.skills.add()
            skill.to_protobuf(container)


class AddSkills(CreateSkills):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
    }

    def _dedupe_skills(self, skill_ids):
        # NOTE: This is subject to a race condition, but since we only have 1
        # interface to add skills we're not going to worry about this for now.
        through_model = models.Profile.skills.through
        current_skill_ids = map(str, through_model.objects.filter(
            profile_id=self.request.profile_id,
        ).values_list('skill_id', flat=True))
        return list(set(skill_ids) - set(current_skill_ids))

    def _add_skills(self, skills):
        skill_ids = [skill.id for skill in skills]
        deduped_skill_ids = self._dedupe_skills(skill_ids)
        through_model = models.Profile.skills.through
        objects = [through_model(
            profile_id=self.request.profile_id,
            skill_id=skill_id,
        ) for skill_id in deduped_skill_ids]
        return through_model.objects.bulk_create(objects)

    def run(self, *args, **kwargs):
        skills_to_create = [skill for skill in self.request.skills if not skill.id]
        skills_to_add = [skill for skill in self.request.skills if skill.id]
        if skills_to_create:
            organization_id = models.Profile.objects.get(
                pk=self.request.profile_id
            ).organization_id
            skills_to_add.extend(self._create_skills(organization_id, skills_to_create))

        if skills_to_add:
            self._add_skills(skills_to_add)


class GetSkills(actions.Action):

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

        skills = models.Skill.objects.filter(**parameters)
        for skill in skills:
            container = self.response.skills.add()
            skill.to_protobuf(container)


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
            'get_team_children',
            team_id=team.id,
            on_error=self.ActionError('ERROR_FETCHING_TEAM_CHILDREN'),
        )
        return [item.owner_id for item in response.result.teams]

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
            ).exclude(pk=profile.id).order_by('first_name', 'last_name')
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
            ).order_by('first_name', 'last_name')
            for item in profiles:
                if item.pk == profile.pk:
                    continue

                container = self.response.profiles.add()
                item.to_protobuf(container)


class GetProfileStats(actions.Action):

    type_validators = {
        'address_ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        stats = models.Profile.objects.filter(address_id__in=self.request.address_ids).values(
            'address_id',
        ).annotate(profiles=Count('id'))
        stats_dict = dict((stat['address_id'], stat['profiles']) for stat in stats)
        for address_id in self.request.address_ids:
            # TODO type validators should check type and then transform to that
            # type so we're working with consistent values. ie. if we validate
            # uuid, we should have "uuid" type, not string
            address_id = uuid.UUID(address_id, version=4)
            container = self.response.stats.add()
            container.id = str(address_id)
            container.count = str(stats_dict.get(address_id, 0))


class GetUpcomingAnniversaries(actions.Action):

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
        profiles = models.Profile.objects.raw(
            self._build_anniversaries_query(),
            self._get_parameters_list(),
        )
        for profile in profiles:
            container = self.response.profiles.add()
            profile.to_protobuf(container)


class GetUpcomingBirthdays(actions.Action):

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
        profiles = models.Profile.objects.raw(
            self._build_birthdays_query(),
            self._get_parameters_list(),
        )
        for profile in profiles:
            container = self.response.profiles.add()
            profile.to_protobuf(container)


class GetRecentHires(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        now = arrow.utcnow()
        profiles = models.Profile.objects.filter(
            organization_id=self.request.organization_id,
            hire_date__gte=now.replace(days=-7).date,
        )
        for profile in profiles:
            container = self.response.profiles.add()
            profile.to_protobuf(container)


class GetActiveSkills(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        skills = set(models.Skill.objects.filter(
            profileskills__skill_id__isnull=False
        ).order_by('-profileskills__created'))
        for skill in skills:
            container = self.response.skills.add()
            skill.to_protobuf(container)
