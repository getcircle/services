from service import (
    actions,
    validators,
)
import service.control

from protobufs.services.feed import containers_pb2 as feed_containers
from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.profile import containers_pb2 as profile_containers


class GetProfileFeed(actions.Action):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    def __init__(self, *args, **kwargs):
        super(GetProfileFeed, self).__init__(*args, **kwargs)
        self.profile_client = service.control.Client('profile', token=self.token)
        self.organization_client = service.control.Client('organization', token=self.token)
        self.note_client = service.control.Client('note', token=self.token)

    def _get_peers_category(self):
        response = self.profile_client.call_action('get_peers', profile_id=self.request.profile_id)
        if not response.success:
            # XXX handle errors properly
            raise Exception('failed to fetch peers')

        if not len(response.result.profiles):
            return

        peers = self.response.categories.add()
        peers.title = 'Peers'
        peers.content_key = 'title'
        peers.category_type = feed_containers.CategoryV1.PEERS
        peers.total_count = len(response.result.profiles)
        for profile in response.result.profiles:
            container = peers.profiles.add()
            container.CopyFrom(profile)

    def _get_direct_reports_category(self):
        response = self.profile_client.call_action(
            'get_direct_reports',
            profile_id=self.request.profile_id,
        )
        if not response.success:
            # XXX handle errors better
            raise Exception('failed to fetch direct reports')

        if not len(response.result.profiles):
            return

        reports = self.response.categories.add()
        reports.title = 'Direct Reports'
        reports.content_key = 'title'
        reports.category_type = feed_containers.CategoryV1.DIRECT_REPORTS
        reports.total_count = len(response.result.profiles)
        for profile in response.result.profiles:
            container = reports.profiles.add()
            container.CopyFrom(profile)

    def _get_upcoming_anniversaries_category(self, profile):
        response = self.profile_client.call_action(
            'get_upcoming_anniversaries',
            organization_id=profile.organization_id,
        )
        if not response.success:
            raise Exception('failed to fetch anniversaries')

        if not len(response.result.profiles):
            return

        anniversaries = self.response.categories.add()
        anniversaries.title = 'Work Anniversaries'
        anniversaries.content_key = 'hire_date'
        anniversaries.category_type = feed_containers.CategoryV1.ANNIVERSARIES
        anniversaries.total_count = len(response.result.profiles)
        # TODO fix this logic in the client
        #for profile in response.result.profiles[:3]:
        for profile in response.result.profiles:
            container = anniversaries.profiles.add()
            container.CopyFrom(profile)

    def _get_upcoming_birthdays_category(self, profile):
        response = self.profile_client.call_action(
            'get_upcoming_birthdays',
            organization_id=profile.organization_id,
        )
        if not response.success:
            raise Exception('failed to fetch birthdays')

        if not len(response.result.profiles):
            return

        birthdays = self.response.categories.add()
        birthdays.title = 'Birthdays'
        birthdays.content_key = 'birth_date'
        birthdays.category_type = feed_containers.CategoryV1.BIRTHDAYS
        birthdays.total_count = len(response.result.profiles)
        #for profile in response.result.profiles[:3]:
        for profile in response.result.profiles:
            container = birthdays.profiles.add()
            container.CopyFrom(profile)

    def _get_recent_hires_category(self, profile):
        response = self.profile_client.call_action(
            'get_recent_hires',
            organization_id=profile.organization_id,
        )
        if not response.success:
            raise Exception('failed to fetch new hires')

        if not len(response.result.profiles):
            return

        hires = self.response.categories.add()
        hires.title = 'New Hires'
        hires.content_key = 'hire_date'
        hires.category_type = feed_containers.CategoryV1.NEW_HIRES
        hires.total_count = len(response.result.profiles)
        #for profile in response.result.profiles[:3]:
        for profile in response.result.profiles:
            container = hires.profiles.add()
            container.CopyFrom(profile)

    def _get_active_skills_or_interests_category(self, organization_id):
        title = 'Skills'
        category_type = feed_containers.CategoryV1.SKILLS
        # See if we have skills to show first
        response = self.profile_client.call_action(
            'get_active_tags',
            organization_id=organization_id,
            tag_type=profile_containers.TagV1.SKILL,
        )
        if not len(response.result.tags):
            # Show interests if we don't have skills
            response = self.profile_client.call_action(
                'get_active_tags',
                organization_id=organization_id,
                tag_type=profile_containers.TagV1.INTEREST,
            )
            if not len(response.result.tags):
                return
            title = 'Interests'
            category_type = feed_containers.CategoryV1.INTERESTS

        tags = self.response.categories.add()
        tags.title = title
        tags.category_type = category_type
        tags.content_key = 'name'
        tags.total_count = response.control.paginator.count
        for tag in response.result.tags:
            container = tags.tags.add()
            container.CopyFrom(tag)

    def _get_profiles_dict(self, profiles):
        return dict((profile.id, profile) for profile in profiles)

    def _get_recent_notes_category(self, profile):
        response = self.note_client.call_action(
            'get_notes',
            owner_profile_id=profile.id,
        )
        if not response.success:
            raise Exception('failed to fetch notes')

        notes = response.result.notes
        if not len(notes):
            return

        response = self.profile_client.call_action(
            'get_profiles',
            ids=[note.for_profile_id for note in notes],
        )
        if not response.success:
            raise Exception('failed to fetch profiles for notes')

        profile_id_to_profile = self._get_profiles_dict(response.result.profiles)

        category = self.response.categories.add()
        category.title = 'Notes'
        category.content_key = 'changed'
        category.category_type = feed_containers.CategoryV1.NOTES
        category.total_count = len(notes)
        for note in notes:
            note_container = category.notes.add()
            note_container.CopyFrom(note)

            profile = profile_id_to_profile[note.for_profile_id]
            profile_container = category.profiles.add()
            profile_container.CopyFrom(profile)

    def _get_group_membership_requests_category(self):
        client = service.control.Client('group', token=self.token)
        response = client.call_action('get_membership_requests')

        requests = response.result.requests
        if not len(requests):
            return

        response = self.profile_client.call_action(
            'get_profiles',
            ids=[request.requester_profile_id for request in requests],
        )
        profile_id_to_profile = self._get_profiles_dict(response.result.profiles)

        response = client.call_action(
            'get_groups',
            group_keys=[request.group_key for request in requests],
            provider=group_containers.GOOGLE,
        )
        group_key_to_group = dict((group.email, group) for group in response.result.groups)

        category = self.response.categories.add()
        category.title = 'Group Membership Requests'
        category.content_key = 'requester_profile_id'
        category.category_type = feed_containers.CategoryV1.GROUP_MEMBERSHIP_REQUESTS
        category.total_count = len(requests)
        for request in requests:
            request_container = category.group_membership_requests.add()
            request_container.CopyFrom(request)

            profile = profile_id_to_profile[request.requester_profile_id]
            profile_container = category.profiles.add()
            profile_container.CopyFrom(profile)

            group = group_key_to_group[request.group_key]
            group_container = category.groups.add()
            group_container.CopyFrom(group)

    def run(self, *args, **kwargs):
        response = self.profile_client.call_action(
            'get_profile',
            profile_id=self.request.profile_id,
        )
        if not response.success:
            raise Exception('failed to fetch profile')

        profile = response.result.profile
        self._get_group_membership_requests_category()
        self._get_recent_notes_category(profile)
        self._get_peers_category()
        self._get_direct_reports_category()
        self._get_recent_hires_category(profile)
        self._get_upcoming_birthdays_category(profile)
        self._get_upcoming_anniversaries_category(profile)
        self._get_active_skills_or_interests_category(profile.organization_id)


class GetOrganizationFeed(GetProfileFeed):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def __init__(self, *args, **kwargs):
        super(GetOrganizationFeed, self).__init__(*args, **kwargs)
        self.organization_client = service.control.Client('organization', token=self.token)
        self.profile_client = service.control.Client('profile', token=self.token)

    def _get_executives(self, organization_id):
        response = self.organization_client.call_action(
            'get_top_level_team',
            organization_id=organization_id,
        )
        if not response.success:
            raise Exception('..fuck!')

        top_level_team = response.result.team
        response = self.profile_client.call_action('get_profile', user_id=top_level_team.owner_id)
        if not response.success:
            raise Exception('fuck!')
        owner = response.result.profile

        response = self.profile_client.call_action(
            'get_direct_reports',
            profile_id=owner.id,
        )
        if not response.success:
            raise Exception('..fuck!')

        executives = []
        executives.extend([owner])
        executives.extend(response.result.profiles)

        category = self.response.categories.add()
        category.title = 'Executives'
        category.content_key = 'name'
        category.category_type = feed_containers.CategoryV1.EXECUTIVES
        category.total_count = len(executives)
        for profile in executives:
            container = category.profiles.add()
            container.CopyFrom(profile)
        return top_level_team

    def _get_departments(self, top_level_team):
        response = self.organization_client.call_action(
            'get_team_descendants',
            team_ids=[top_level_team.id],
            depth=1,
        )
        # XXX remove all of these places i wasn't handling if one of these calls raises an error
        if not response.success:
            raise Exception('..fuck!')

        departments = []
        departments.extend([top_level_team])

        descendants = response.result.descendants[0]
        departments.extend(descendants.teams)

        category = self.response.categories.add()
        category.title = 'Departments'
        category.content_key = 'name'
        category.category_type = feed_containers.CategoryV1.DEPARTMENTS
        category.total_count = len(departments)
        for department in departments:
            container = category.teams.add()
            container.CopyFrom(department)

    def _get_locations_category(self, organization_id):
        response = self.organization_client.call_action(
            'get_locations',
            organization_id=organization_id,
        )
        if not response.success:
            raise Exception('failed to fetch locations')

        if not len(response.result.locations):
            return

        items = response.result.locations
        locations = self.response.categories.add()
        locations.title = 'Locations'
        locations.content_key = 'address_1'
        locations.category_type = feed_containers.CategoryV1.LOCATIONS
        locations.total_count = len(items)
        for location in items:
            container = locations.locations.add()
            container.CopyFrom(location)

    def run(self, *args, **kwargs):
        top_level_team = self._get_executives(self.request.organization_id)
        self._get_locations_category(self.request.organization_id)
        self._get_departments(top_level_team)
