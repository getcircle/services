import service.control
import service.settings
from protobufs.services.feed import containers_pb2 as feed_containers
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
        self.client = service.control.Client('feed', token='test-token')
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

    def _mock_get_locations(self, organization_id, locations=3):
        service = 'organization'
        action = 'get_locations'
        mock_response = mock.get_mockable_response(service, action)
        for _ in range(locations):
            location = mock_response.locations.add()
            mocks.mock_location(location, organization_id=organization_id)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            organization_id=organization_id,
        )
        return mock_response.locations

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

    def _mock_get_team_descendants(self, team_id, teams=3):
        service = 'organization'
        action = 'get_team_descendants'
        mock_response = mock.get_mockable_response(service, action)
        descendants = mock_response.descendants.add()
        descendants.parent_team_id = team_id
        for _ in range(teams):
            team = descendants.teams.add()
            mocks.mock_team(team)

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            team_ids=[team_id],
            depth=1,
        )
        return mock_response.descendants

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

    def test_get_organization_feed_invalid_organization_id(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_organization_feed', organization_id='invalid')

    def test_get_organization_feed(self):
        organization = self._mock_get_organization()
        locations = self._mock_get_locations(organization.id)
        top_level_team = self._mock_get_top_level_team(organization.id)
        self._mock_get_team_descendants(top_level_team.id, teams=5)
        owner = self._mock_get_profile_with_user_id(top_level_team.owner_id)
        self._mock_get_direct_reports(owner.id)

        response = self.client.call_action(
            'get_organization_feed',
            organization_id=organization.id,
        )
        self.assertTrue(response.success)

        category_dict = dict((res.type, res) for res in response.result.categories)

        location_category = category_dict[feed_containers.CategoryV1.LOCATIONS]
        self.assertEqual(len(location_category.locations), len(locations))

        executives = category_dict[feed_containers.CategoryV1.EXECUTIVES]
        # equal to 4 because we include the owner (the rest are just direct reports)
        self.assertEqual(len(executives.profiles), 4)
        self._verify_containers(owner, executives.profiles[0])

        departments = category_dict[feed_containers.CategoryV1.DEPARTMENTS]
        # top level team should be the first "department" listed
        self._verify_containers(top_level_team, departments.teams[0])
        # equal to 6 because we include the top level team
        self.assertEqual(len(departments.teams), 6)
