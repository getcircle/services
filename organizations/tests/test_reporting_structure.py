import service.control
from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import (
    factories,
    models,
)


class OrganizationTeamTests(MockedTestCase):

    def setUp(self):
        super(OrganizationTeamTests, self).setUp()
        self.organization = factories.OrganizationFactory.create()
        self.profile = mocks.mock_profile(organization_id=str(self.organization.id))
        self.client = service.control.Client(
            'organization',
            token=mocks.mock_token(
                organization_id=str(self.organization.id),
                profile_id=self.profile.id,
            ),
        )
        self.mock.instance.dont_mock_service('organization')

    def test_add_direct_reports_invalid_manager_profile_id(self):
        direct_reports_profile_ids = [fuzzy.FuzzyUUID().fuzz() for _ in range(2)]
        with self.assertFieldError('manager_profile_id'):
            self.client.call_action(
                'add_direct_reports',
                manager_profile_id='invalid',
                direct_reports_profile_ids=direct_reports_profile_ids,
            )

    def test_add_direct_reports_manager_profile_id_required(self):
        direct_reports_profile_ids = [fuzzy.FuzzyUUID().fuzz() for _ in range(2)]
        with self.assertFieldError('manager_profile_id', 'MISSING'):
            self.client.call_action(
                'add_direct_reports',
                direct_reports_profile_ids=direct_reports_profile_ids,
            )

    def test_add_direct_reports_direct_reports_profile_ids_required(self):
        with self.assertFieldError('direct_reports_profile_ids', 'MISSING'):
            self.client.call_action(
                'add_direct_reports',
                manager_profile_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_add_direct_reports_invalid_direct_reports_profile_ids(self):
        with self.assertFieldError('direct_reports_profile_ids'):
            self.client.call_action(
                'add_direct_reports',
                manager_profile_id=fuzzy.FuzzyUUID().fuzz(),
                direct_reports_profile_ids=['invalid'],
            )

    def test_add_direct_reports_no_existing_team(self):
        direct_reports_profile_ids = [fuzzy.FuzzyUUID().fuzz() for _ in range(2)]
        manager_profile_id = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action(
            'add_direct_reports',
            manager_profile_id=manager_profile_id,
            direct_reports_profile_ids=direct_reports_profile_ids,
        )
        self.assertEqual(response.result.team.profile_count, 3)
        self.assertEqual(response.result.team.child_team_count, 0)

    def test_add_direct_reports_exist_team(self):
        # create an existing team (auto creates manager and direct report)
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        response = self.client.call_action(
            'add_direct_reports',
            manager_profile_id=team.manager_profile_id,
            direct_reports_profile_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        self.verify_containers(team, response.result.team, ignore_fields=('profile_count',))
        manager = models.ReportingStructure.objects.get(profile_id=team.manager_profile_id)
        self.assertEqual(manager.get_descendant_count(), 2)

    def test_set_manager_manager_profile_id_required(self):
        with self.assertFieldError('manager_profile_id', 'MISSING'):
            self.client.call_action('set_manager', profile_id=fuzzy.FuzzyUUID().fuzz())

    def test_set_manager_manager_profile_id_invalid(self):
        with self.assertFieldError('manager_profile_id'):
            self.client.call_action(
                'set_manager',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
                manager_profile_id='invalid',
            )

    def test_set_manager_profile_id_required(self):
        with self.assertFieldError('profile_id', 'MISSING'):
            self.client.call_action('set_manager', manager_profile_id=fuzzy.FuzzyUUID().fuzz())

    def test_set_manager_profile_id_invalid(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'set_manager',
                manager_profile_id=fuzzy.FuzzyUUID().fuzz(),
                profile_id='invalid',
            )

    def test_set_manager(self):
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        response = self.client.call_action(
            'set_manager',
            profile_id=self.profile.id,
            manager_profile_id=team.manager_profile_id,
        )
        self.verify_containers(team, response.result.team, ignore_fields=('profile_count',))
        manager = models.ReportingStructure.objects.get(profile_id=team.manager_profile_id)
        self.assertEqual(manager.get_descendant_count(), 2)
        report = models.ReportingStructure.objects.get(profile_id=self.profile.id)
        self.assertEqualUUID4(report.added_by_profile_id, self.profile.id)
        self.assertEqualUUID4(report.manager_id, manager.profile_id)

    def test_get_profile_reporting_details_does_not_exist(self):
        response = self.client.call_action(
            'get_profile_reporting_details',
            profile_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self.assertFalse(response.result.HasField('manages_team'))
        self.assertFalse(response.result.HasField('team'))
        self.assertFalse(response.result.peers_profile_ids)
        self.assertFalse(response.result.manager_profile_id)
        self.assertFalse(response.result.direct_reports_profile_ids)

    def test_get_profile_reporting_details_profile_id_required(self):
        with self.assertFieldError('profile_id', 'MISSING'):
            self.client.call_action('get_profile_reporting_details')

    def test_get_profile_reporting_details_profile_id_invalid(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_profile_reporting_details', profile_id='invalid')

    def test_get_profile_reporting_details(self):
        # create a team, manager, and direct_report
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = models.ReportingStructure.objects.get(profile_id=team.manager_profile_id)
        # create another team whose manager is the above direct report
        sub_team = factories.TeamFactory.create_protobuf(
            organization=self.organization,
            manager_profile_id=manager.get_children()[0].profile_id,
        )
        sub_manager = models.ReportingStructure.objects.get(profile_id=sub_team.manager_profile_id)
        # add a peer to the sub team's manager
        peer = factories.ReportingStructureFactory.create(
            organization=self.organization,
            manager=manager,
        )
        response = self.client.call_action(
            'get_profile_reporting_details',
            profile_id=sub_team.manager_profile_id,
        )
        self.assertEqual(len(response.result.peers_profile_ids), 1)
        self.assertEqualUUID4(response.result.peers_profile_ids[0], peer.profile_id)
        self.assertEqual(len(response.result.direct_reports_profile_ids), 1)
        self.assertEqualUUID4(
            response.result.direct_reports_profile_ids[0],
            sub_manager.get_children()[0].profile_id,
        )
        self.assertEqualUUID4(response.result.manager_profile_id, manager.profile_id)
        self.verify_containers(
            team,
            response.result.team,
            ignore_fields=('profile_count', 'child_team_count'),
        )
        self.verify_containers(
            sub_team,
            response.result.manages_team,
            ignore_fields=('profile_count'),
        )
