import service.control
import service.settings
from protobufs.landing_service_pb2 import LandingService
from service.transports import (
    local,
    mock,
)
from services.test import (
    mocks,
    TestCase,
)


class TestGetExtendedOrganization(TestCase):

    def setUp(self):
        super(TestGetExtendedOrganization, self).setUp()
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        self.client = service.control.Client('landing', token='test-token')
        self.client.set_transport(local.instance)

    def tearDown(self):
        super(TestGetExtendedOrganization, self).tearDown()

    def _mock_get_organization(self, organization_id=None):
        service = 'organization'
        action = 'get_organization'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_organization(mock_response.organization)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=mock_response.organization.id,
        )
        return mock_response.organization

    def _mock_get_active_tags(self, organization_id, tags=3):
        service = 'profile'
        action = 'get_active_tags'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(tags):
            tag = mock_response.tags.add()
            mocks.mock_tag(tag)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
        )
        return mock_response.tags

    def _mock_get_addresses(self, organization_id, addresses=3):
        service = 'organization'
        action = 'get_addresses'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(addresses):
            address = mock_response.addresses.add()
            mocks.mock_address(address, organization_id=organization_id)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
        )
        return mock_response.addresses

    def _mock_get_top_level_team(self, organization_id):
        service = 'organization'
        action = 'get_top_level_team'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_team(mock_response.team, organization_id=organization_id)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
        )
        return mock_response.team

    def _mock_get_team_children(self, team_id, teams=3):
        service = 'organization'
        action = 'get_team_children'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(teams):
            team = mock_response.teams.add()
            mocks.mock_team(team)

        mock.instance.register_mock_response(service, action, mock_response, team_id=team_id)
        return mock_response.teams

    def _mock_get_direct_reports(self, profile_id, reports=3):
        service = 'profile'
        action = 'get_direct_reports'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(reports):
            profile = mock_response.profiles.add()
            mocks.mock_profile(profile)

        mock.instance.register_mock_response(service, action, mock_response, profile_id=profile_id)
        return mock_response.profiles

    def _mock_get_profile_with_user_id(self, user_id):
        service = 'profile'
        action = 'get_profile'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_profile(mock_response.profile, user_id=user_id)
        mock.instance.register_mock_response(service, action, mock_response, user_id=user_id)
        return mock_response.profile

    def _mock_get_profile_stats(self, address_ids, count=3):
        service = 'profile'
        action = 'get_profile_stats'
        mock_response = mock.get_mockable_response(service, action)
        for address_id in address_ids:
            container = mock_response.stats.add()
            container.id = address_id
            container.count = str(count)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            address_ids=address_ids,
        )

    def test_get_organization_categories_invalid_organization_id(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_organization_categories', organization_id='invalid')

    def test_get_organization_categories(self):
        organization = self._mock_get_organization()
        trending_tags = self._mock_get_active_tags(organization.id, tags=10)
        addresses = self._mock_get_addresses(organization.id)
        self._mock_get_profile_stats([address.id for address in addresses])
        top_level_team = self._mock_get_top_level_team(organization.id)
        self._mock_get_team_children(top_level_team.id, teams=5)
        owner = self._mock_get_profile_with_user_id(top_level_team.owner_id)
        self._mock_get_direct_reports(owner.id)

        response = self.client.call_action(
            'get_organization_categories',
            organization_id=organization.id,
        )
        self.assertTrue(response.success)

        category_dict = dict((res.type, res) for res in response.result.categories)

        tags = category_dict[LandingService.Containers.Category.TAGS]
        self.assertEqual(len(tags.tags), len(trending_tags))

        locations = category_dict[LandingService.Containers.Category.LOCATIONS]
        self.assertEqual(len(locations.addresses), len(addresses))

        executives = category_dict[LandingService.Containers.Category.EXECUTIVES]
        # equal to 4 because we include the owner (the rest are just direct reports)
        self.assertEqual(len(executives.profiles), 4)
        self._verify_containers(owner, executives.profiles[0])

        departments = category_dict[LandingService.Containers.Category.DEPARTMENTS]
        # top level team should be the first "department" listed
        self._verify_containers(top_level_team, departments.teams[0])
        # equal to 6 because we include the top level team
        self.assertEqual(len(departments.teams), 6)
