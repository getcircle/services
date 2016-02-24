import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )
        self.client = service.control.Client('team', token=self.token)
        self.mock.instance.dont_mock_service('team')

    def test_get_teams_wrong_organization(self):
        factories.TeamFactory.create_batch(size=5, organization_id=fuzzy.uuid())
        response = self.client.call_action('get_teams')
        self.assertEqual(len(response.result.teams), 0)

    def test_get_teams(self):
        expected = factories.TeamFactory.create_batch(size=5, organization_id=self.organization.id)
        response = self.client.call_action('get_teams')
        self.assertEqual(len(response.result.teams), len(expected))

    def test_get_teams_by_ids(self):
        fetched = factories.TeamFactory.create_batch(size=2, organization_id=self.organization.id)
        factories.TeamFactory.create_batch(size=3, organization_id=self.organization.id)
        response = self.client.call_action('get_teams', ids=[str(t.id) for t in fetched])
        self.assertEqual(len(response.result.teams), len(fetched))

        fetched_ids = [t.id for t in response.result.teams]
        for team in fetched:
            self.assertIn(str(team.id), fetched_ids)

    def test_get_teams_by_ids_invalid_values(self):
        with self.assertFieldError('ids'):
            self.client.call_action('get_teams', ids=['invalid', 'invalid'])
