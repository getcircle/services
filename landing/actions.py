from service import (
    actions,
    validators,
)
import service.control

from protobufs.landing_service_pb2 import LandingService


class GetCategories(actions.Action):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    def __init__(self, *args, **kwargs):
        super(GetCategories, self).__init__(*args, **kwargs)
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
        peers.type = LandingService.Containers.Category.PEERS
        peers.total_count = str(len(response.result.profiles))
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
        reports.type = LandingService.Containers.Category.DIRECT_REPORTS
        reports.total_count = str(len(response.result.profiles))
        for profile in response.result.profiles:
            container = reports.profiles.add()
            container.CopyFrom(profile)

    def _get_locations_category(self, organization_id):
        response = self.organization_client.call_action(
            'get_addresses',
            organization_id=organization_id,
        )
        if not response.success:
            raise Exception('failed to fetch addresses')

        if not len(response.result.addresses):
            return

        addresses = response.result.addresses
        address_ids = [address.id for address in addresses]
        response = self.profile_client.call_action('get_profile_stats', address_ids=address_ids)
        if not response.success:
            raise Exception('failed to fetch profile stats')

        stats = dict((stat.id, stat.count) for stat in response.result.stats)
        locations = self.response.categories.add()
        locations.title = 'Locations'
        locations.content_key = 'address_1'
        locations.type = LandingService.Containers.Category.LOCATIONS
        locations.total_count = str(len(addresses))
        for address in addresses:
            container = locations.addresses.add()
            container.CopyFrom(address)
            container.profile_count = str(stats.get(address.id, 0))

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
        anniversaries.type = LandingService.Containers.Category.ANNIVERSARIES
        anniversaries.total_count = str(len(response.result.profiles))
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
        birthdays.type = LandingService.Containers.Category.BIRTHDAYS
        birthdays.total_count = str(len(response.result.profiles))
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
        hires.type = LandingService.Containers.Category.NEW_HIRES
        hires.total_count = str(len(response.result.profiles))
        #for profile in response.result.profiles[:3]:
        for profile in response.result.profiles:
            container = hires.profiles.add()
            container.CopyFrom(profile)

    def _get_active_skills_category(self, organization_id):
        response = self.profile_client.call_action(
            'get_active_skills',
            organization_id=organization_id,
        )
        if not response.success:
            raise Exception('failed ot fetch trending skills')

        if not len(response.result.skills):
            return

        skills = self.response.categories.add()
        skills.title = 'Skills'
        skills.content_key = 'name'
        skills.type = LandingService.Containers.Category.SKILLS
        skills.total_count = str(len(response.result.skills))
        for skill in response.result.skills:
            container = skills.skills.add()
            container.CopyFrom(skill)

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

        profile_id_to_profile = dict((profile.id, profile) for profile in response.result.profiles)

        category = self.response.categories.add()
        category.title = 'Notes'
        category.content_key = 'changed'
        category.type = LandingService.Containers.Category.NOTES
        category.total_count = str(len(notes))
        for note in notes:
            note_container = category.notes.add()
            note_container.CopyFrom(note)

            profile = profile_id_to_profile[note.for_profile_id]
            profile_container = category.profiles.add()
            profile_container.CopyFrom(profile)

    def run(self, *args, **kwargs):
        response = self.profile_client.call_action(
            'get_profile',
            profile_id=self.request.profile_id,
        )
        if not response.success:
            raise Exception('failed to fetch profile')

        profile = response.result.profile
        self._get_recent_notes_category(profile)
        self._get_peers_category()
        self._get_direct_reports_category()
        self._get_locations_category(profile.organization_id)
        self._get_upcoming_birthdays_category(profile)
        self._get_upcoming_anniversaries_category(profile)
        self._get_recent_hires_category(profile)
        self._get_active_skills_category(profile.organization_id)


class GetOrganizationCategories(GetCategories):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def __init__(self, *args, **kwargs):
        super(GetOrganizationCategories, self).__init__(*args, **kwargs)
        self.organization_client = service.control.Client('organization', token=self.token)
        self.profile_client = service.control.Client('profile', token=self.token)

    def _get_departments_and_executives(self, organization_id):
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
        category.type = LandingService.Containers.Category.EXECUTIVES
        category.total_count = str(len(executives))
        for profile in executives:
            container = category.profiles.add()
            container.CopyFrom(profile)

        response = self.organization_client.call_action(
            'get_team_children',
            team_id=top_level_team.id,
        )
        if not response.success:
            raise Exception('..fuck!')

        departments = []
        departments.extend([top_level_team])
        departments.extend(response.result.teams)

        category = self.response.categories.add()
        category.title = 'Departments'
        category.content_key = 'name'
        category.type = LandingService.Containers.Category.DEPARTMENTS
        category.total_count = str(len(departments))
        for department in departments:
            container = category.teams.add()
            container.CopyFrom(department)

    def run(self, *args, **kwargs):
        self._get_departments_and_executives(self.request.organization_id)
        self._get_locations_category(self.request.organization_id)
        self._get_active_skills_category(self.request.organization_id)
