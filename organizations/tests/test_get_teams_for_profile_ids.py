import service.control
from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories


class TestGetTeamsForProfileIds(MockedTestCase):

    def setUp(self):
        super(TestGetTeamsForProfileIds, self).setUp()
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

    def test_get_teams_for_profile_ids_profile_ids_required(self):
        with self.assertFieldError('profile_ids', 'MISSING'):
            self.client.call_action('get_teams_for_profile_ids')

    def test_get_teams_for_profile_ids_profile_ids_invalid(self):
        with self.assertFieldError('profile_ids'):
            self.client.call_action('get_teams_for_profile_ids', profile_ids=['invalid'])

    def test_get_teams_for_profile_ids(self):
        manager = factories.ReportingStructureFactory.create(
            manager=None,
            organization=self.organization,
        )
        # create a few reports to this manager
        report_1 = factories.ReportingStructureFactory.create(
            manager=manager,
            organization=self.organization,
        )
        report_2 = factories.ReportingStructureFactory.create(
            manager=manager,
            organization=self.organization,
        )

        # create another manager with 1 report
        report_3 = factories.ReportingStructureFactory.create(
            manager=factories.ReportingStructureFactory.create(
                manager=None,
                organization=self.organization,
            ),
            organization=self.organization,
        )

        # create teams for the two managers
        manager_1_team = factories.TeamFactory.create_protobuf(
            organization=self.organization,
            manager_profile_id=manager.profile_id,
        )
        manager_2_team = factories.TeamFactory.create_protobuf(
            organization=self.organization,
            manager_profile_id=report_3.manager_id,
        )

        # fetch the teams for the reports
        response = self.client.call_action(
            'get_teams_for_profile_ids',
            profile_ids=[str(p.profile_id) for p in [report_1, report_2, report_3]],
        )
        self.assertEqual(len(response.result.profiles_teams), 3)
        profiles_teams_dict = dict((p.profile_id, p.team) for p in response.result.profiles_teams)

        report_1_team = profiles_teams_dict[str(report_1.profile_id)]
        self.verify_containers(report_1_team, manager_1_team)
        report_2_team = profiles_teams_dict[str(report_2.profile_id)]
        self.verify_containers(report_2_team, manager_1_team)
        report_3_team = profiles_teams_dict[str(report_3.profile_id)]
        self.verify_containers(report_3_team, manager_2_team)

        # only fetch team name
        response = self.client.call_action(
            'get_teams_for_profile_ids',
            profile_ids=[str(p.profile_id) for p in [report_1, report_2, report_3]],
            fields={'only': ['name']},
        )
        team = response.result.profiles_teams[0].team
        self.assertEqual(len(team.ListFields()), 1)
