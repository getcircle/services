import service.control
import service.settings
from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class TestGetExtendedProfile(MockedTestCase):

    def setUp(self):
        super(TestGetExtendedProfile, self).setUp()
        self._mock_display_title()
        self.organization = mocks.mock_organization()
        self.profile = factories.ProfileFactory.create_protobuf(
            organization_id=self.organization.id,
        )
        self.token = mocks.mock_token(
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        self.client = service.control.Client('profile', token=self.token)
        # mock identities for all calls
        self.identities = self._mock_get_identities()
        self.mock.instance.dont_mock_service('profile')

    def _mock_display_title(self):
        self.mock.instance.register_empty_response(
            service='organization',
            action='get_teams_for_profile_ids',
            mock_regex_lookup='organization:get_teams_for_profile_ids:.*',
        )

    def _mock_get_identities(self, count=3, **overrides):
        service = 'user'
        action = 'get_identities'
        mock_response = self.mock.get_mockable_response(service, action)
        for _ in range(count):
            container = mock_response.identities.add()
            mocks.mock_identity(container)

        self.mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            mock_regex_lookup='%s:%s:.*' % (service, action),
        )
        return mock_response.identities

    def _mock_get_profile_reporting_structure(
        self,
        profile,
        peers,
        manager,
        direct_reports,
        manages_team,
        team,
    ):
        service = 'organization'
        action = 'get_profile_reporting_details'
        mock_response = self.mock.get_mockable_response(service, action)
        mock_response.peers_profile_ids.extend([str(p.id) for p in peers])
        mock_response.direct_reports_profile_ids.extend([str(d.id) for d in direct_reports])
        mock_response.manager_profile_id = str(manager.id)
        mock_response.manages_team.CopyFrom(manages_team)
        mock_response.team.CopyFrom(team)
        self.mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            profile_id=profile.id,
        )

    def test_get_extended_profile_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'get_extended_profile',
                profile_id='invalid',
            )

    def test_get_extended_profile_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_extended_profile',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_extended_profile(self):
        manager = factories.ProfileFactory.create_protobuf(organization_id=self.organization.id)
        profile = factories.ProfileFactory.create_protobuf(organization_id=self.organization.id)

        # setup mock objects
        # 3 peers
        peers = factories.ProfileFactory.create_batch(
            size=3,
            organization_id=self.organization.id,
        )
        # 3 direct reports
        direct_reports = factories.ProfileFactory.create_batch(
            size=3,
            organization_id=self.organization.id,
        )
        # 2 locations
        locations = [
            mocks.mock_location(organization_id=self.organization.id),
            mocks.mock_location(organization_id=self.organization.id),
        ]
        team = mocks.mock_team(
            organization_id=self.organization.id,
            manager_profile_id=manager.id,
        )
        manages_team = mocks.mock_team(
            organization_id=self.organization.id,
            manager_profile_id=profile.id,
        )

        # setup mock service calls
        self.mock.instance.register_mock_object(
            'organization',
            'get_locations',
            return_object_path='locations',
            return_object=locations,
            profile_id=profile.id,
            inflations={'only': ['profile_count']},
        )
        self._mock_get_profile_reporting_structure(
            profile=profile,
            peers=peers,
            direct_reports=direct_reports,
            team=team,
            manages_team=manages_team,
            manager=manager,
        )

        response = self.client.call_action('get_extended_profile', profile_id=profile.id)
        self.verify_containers(manager, response.result.manager)
        self.assertEqual(len(response.result.locations), len(locations))
        self.verify_containers(team, response.result.team)
        self.verify_containers(profile, response.result.profile)
        self.assertEqual(len(direct_reports), len(response.result.direct_reports))
        self.assertEqual(len(self.identities), len(response.result.identities))

    def test_get_extended_profile_no_reporting_info(self):
        # setup mock service calls
        self.mock.instance.register_empty_response(
            'organization',
            'get_locations',
            profile_id=self.profile.id,
            inflations={'only': ['profile_count']},
        )
        self.mock.instance.register_empty_response(
            'organization',
            'get_profile_reporting_details',
            profile_id=self.profile.id,
        )

        response = self.client.call_action('get_extended_profile', profile_id=self.profile.id)
        self.assertFalse(response.result.HasField('manager'))
        self.assertFalse(response.result.locations)
        self.assertFalse(response.result.HasField('team'))
        self.assertFalse(response.result.HasField('manages_team'))
        self.verify_containers(self.profile, response.result.profile)
        self.assertEqual(len(self.identities), len(response.result.identities))
