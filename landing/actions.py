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
        peers.category_type = LandingService.PEERS
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
        reports.category_type = LandingService.DIRECT_REPORTS
        reports.total_count = str(len(response.result.profiles))
        for profile in response.result.profiles:
            container = reports.profiles.add()
            container.CopyFrom(profile)

    def _get_locations_category(self, profile):
        response = self.organization_client.call_action(
            'get_addresses',
            organization_id=profile.organization_id,
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
        locations.category_type = LandingService.LOCATIONS
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
        anniversaries.category_type = LandingService.ANNIVERSARIES
        anniversaries.total_count = str(len(response.result.profiles))
        for profile in response.result.profiles[:3]:
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
        birthdays.category_type = LandingService.BIRTHDAYS
        birthdays.total_count = str(len(response.result.profiles))
        for profile in response.result.profiles[:3]:
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
        hires.category_type = LandingService.NEW_HIRES
        hires.total_count = str(len(response.result.profiles))
        for profile in response.result.profiles[:3]:
            container = hires.profiles.add()
            container.CopyFrom(profile)

    def run(self, *args, **kwargs):
        response = self.profile_client.call_action(
            'get_profile',
            profile_id=self.request.profile_id,
        )
        if not response.success:
            raise Exception('failed to fetch profile')

        profile = response.result.profile
        self._get_peers_category()
        self._get_direct_reports_category()
        self._get_locations_category(profile)
        self._get_upcoming_anniversaries_category(profile)
        self._get_upcoming_birthdays_category(profile)
        self._get_recent_hires_category(profile)
