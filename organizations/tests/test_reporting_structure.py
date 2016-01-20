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

    def test_add_direct_reports_invalid_profile_id(self):
        direct_reports_profile_ids = [fuzzy.FuzzyUUID().fuzz() for _ in range(2)]
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'add_direct_reports',
                profile_id='invalid',
                direct_reports_profile_ids=direct_reports_profile_ids,
            )

    def test_add_direct_reports_profile_id_required(self):
        direct_reports_profile_ids = [fuzzy.FuzzyUUID().fuzz() for _ in range(2)]
        with self.assertFieldError('profile_id', 'MISSING'):
            self.client.call_action(
                'add_direct_reports',
                direct_reports_profile_ids=direct_reports_profile_ids,
            )

    def test_add_direct_reports_direct_reports_profile_ids_required(self):
        with self.assertFieldError('direct_reports_profile_ids', 'MISSING'):
            self.client.call_action(
                'add_direct_reports',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_add_direct_reports_invalid_direct_reports_profile_ids(self):
        with self.assertFieldError('direct_reports_profile_ids'):
            self.client.call_action(
                'add_direct_reports',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
                direct_reports_profile_ids=['invalid'],
            )

    def test_add_direct_reports_no_existing_team(self):
        direct_reports_profile_ids = [fuzzy.FuzzyUUID().fuzz() for _ in range(2)]
        profile_id = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action(
            'add_direct_reports',
            profile_id=profile_id,
            direct_reports_profile_ids=direct_reports_profile_ids,
        )
        self.assertEqual(response.result.team.profile_count, 3)
        self.assertEqual(response.result.team.child_team_count, 0)
        self.assertTrue(response.result.created)

    def test_add_direct_reports_exist_team(self):
        # create an existing team (auto creates manager and direct report)
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        response = self.client.call_action(
            'add_direct_reports',
            profile_id=team.manager_profile_id,
            direct_reports_profile_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        self.verify_containers(team, response.result.team, ignore_fields=('profile_count',))
        manager = models.ReportingStructure.objects.get(profile_id=team.manager_profile_id)
        self.assertEqual(manager.get_descendant_count(), 2)
        self.assertFalse(response.result.created)

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
        self.assertFalse(response.result.manages_team.ByteSize())
        self.assertFalse(response.result.team.ByteSize())
        self.assertFalse(response.result.peers_profile_ids)
        self.assertFalse(response.result.manager_profile_id)
        self.assertFalse(response.result.direct_reports_profile_ids)

    def test_get_profile_reporting_details_profile_id_invalid(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_profile_reporting_details', profile_id='invalid')

    def test_get_profile_reporting_details_default_token_profile_id(self):
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = models.ReportingStructure.objects.get(profile_id=team.manager_profile_id)
        models.ReportingStructure.objects.create(
            profile_id=self.profile.id,
            manager=manager,
            organization=self.organization,
        )
        response = self.client.call_action('get_profile_reporting_details')
        self.assertEqual(response.result.manager_profile_id, str(manager.profile_id))

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

    def test_get_team_reporting_details_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('get_team_reporting_details')

    def test_get_team_reporting_details_team_id_invalid(self):
        with self.assertFieldError('team_id'):
            self.client.call_action(
                'get_team_reporting_details',
                team_id='invalid',
            )

    def test_get_team_reporting_details_team_id_does_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'get_team_reporting_details',
                team_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_get_team_reporting_details(self):
        # create a team, manager, and direct_report
        team = factories.TeamFactory.create_protobuf(organization=self.organization)
        manager = models.ReportingStructure.objects.get(profile_id=team.manager_profile_id)
        # create another team whose manager is the above direct report
        sub_team = factories.TeamFactory.create_protobuf(
            organization=self.organization,
            manager_profile_id=manager.get_children()[0].profile_id,
        )
        # add a peer to the sub team's manager
        factories.ReportingStructureFactory.create(
            organization=self.organization,
            manager=manager,
        )

        self.mock.instance.register_mock_object(
            'profile',
            'get_profile',
            return_object_path='profile',
            return_object=mocks.mock_profile(id=str(manager.profile_id)),
            profile_id=str(manager.profile_id),
            inflations={'enabled': False},
        )
        response = self.client.call_action('get_team_reporting_details', team_id=team.id)
        self.assertEqual(len(response.result.child_teams), 1)
        self.verify_containers(
            sub_team,
            response.result.child_teams[0],
            ignore_fields=(
                'profile_count',
                'chid_team_count',
            ),
        )
        self.assertEqualUUID4(manager.profile_id, response.result.manager.id)

    def test_get_descendants_profile_id_invalid(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_descendants', profile_id='invalid')

    def test_get_descendants_profile_id_required(self):
        with self.assertFieldError('profile_id', 'MISSING'):
            self.client.call_action('get_descendants')

    def test_get_descendants_profile_id_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_descendants', profile_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_descendants(self):
        manager = factories.ReportingStructureFactory.create(
            manager=None,
            organization=self.organization,
        )
        # create some middle managers
        factories.ReportingStructureFactory.create_batch(
            size=3,
            manager=manager,
            organization=self.organization,
        )
        # create the middle manager who will query about
        middle_manager = factories.ReportingStructureFactory.create(
            manager=manager,
            organization=self.organization,
        )
        # create children
        child = factories.ReportingStructureFactory.create_batch(
            size=3,
            manager=middle_manager,
            organization=self.organization,
        )[0]
        # create grandchildren
        factories.ReportingStructureFactory.create_batch(
            size=3,
            manager=child,
            organization=self.organization,
        )

        response = self.client.call_action('get_descendants', profile_id=middle_manager.profile_id)
        self.assertEqual(len(response.result.profile_ids), 6)

    def test_get_descendants_team_id_invalid(self):
        with self.assertFieldError('team_id'):
            self.client.call_action('get_descendants', team_id='invalid')

    def test_get_descendants_team_id_does_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_descendants', team_id=fuzzy.FuzzyUUID().fuzz())

    def test_get_descendants_team_id(self):
        manager = factories.ReportingStructureFactory.create(
            manager=None,
            organization=self.organization,
        )
        # create some middle managers
        factories.ReportingStructureFactory.create_batch(
            size=3,
            manager=manager,
            organization=self.organization,
        )
        # create the middle manager who will query about
        middle_manager = factories.ReportingStructureFactory.create(
            manager=manager,
            organization=self.organization,
        )
        # create the team we'll query for (implicitly creates 1 direct report)
        team = factories.TeamFactory.create(
            manager_profile_id=middle_manager.profile_id,
            organization=self.organization,
        )
        # create children
        child = factories.ReportingStructureFactory.create_batch(
            size=3,
            manager=middle_manager,
            organization=self.organization,
        )[0]
        # create grandchildren
        factories.ReportingStructureFactory.create_batch(
            size=3,
            manager=child,
            organization=self.organization,
        )

        response = self.client.call_action('get_descendants', team_id=str(team.id))
        # results should include the manager + 6 descendants
        self.assertEqual(len(response.result.profile_ids), 8)
