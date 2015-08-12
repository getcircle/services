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
