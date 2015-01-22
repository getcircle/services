import service.control
import service.settings
from service.transports import (
    local,
    mock,
)
from services.test import (
    fuzzy,
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

    def test_get_extended_organization_invalid_organization_id(self):
        response = self.client.call_action('get_extended_organization', organization_id='invalid')
        self._verify_field_error(response, 'organization_id')

    def test_get_extended_organization(self):
        organization = self._mock_get_organization()
        trending_tags = self._mock_get_active_tags(organization.id, tags=10)
        addresses = self._mock_get_addresses(organization.id)
        top_level_team = self._mock_get_top_level_team(organization.id)
        self._mock_get_team_children(top_level_team.id, teams=5)
        owner = self._mock_get_profile_with_user_id(top_level_team.owner_id)
        self._mock_get_direct_reports(owner.id)

        response = self.client.call_action(
            'get_extended_organization',
            organization_id=organization.id,
        )
        self.assertTrue(response.success)
        self._verify_containers(organization, response.result.organization)
        self.assertEqual(len(response.result.trending_tags), len(trending_tags))
        self.assertEqual(len(response.result.addresses), len(addresses))
        # equal to 6 because we include the top level team
        self.assertEqual(len(response.result.departments), 6)
        # top level team should be the first "department" listed
        self._verify_containers(top_level_team, response.result.departments[0])
        # equal to 4 because we include the owner (the rest are just direct reports)
        self.assertEqual(len(response.result.executives), 4)
        self._verify_containers(owner, response.result.executives[0])
