from protobufs.services.team import containers_pb2 as team_containers
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

    def _setup_coordinator(self, **overrides):
        team = factories.TeamFactory.create(organization_id=self.organization.id, **overrides)
        factories.TeamMemberFactory.create(
            team=team,
            role=team_containers.TeamMemberV1.COORDINATOR,
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        return team.to_protobuf()

    def test_update_team_team_required(self):
        with self.assertFieldError('team', 'MISSING'):
            self.client.call_action('update_team')

    def test_update_team_team_does_not_exist(self):
        team = factories.TeamFactory.build_protobuf()
        with self.assertFieldError('team.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_team', team=team)

    def test_update_team_wrong_organization(self):
        team = factories.TeamFactory.create_protobuf()
        with self.assertFieldError('team.id', 'DOES_NOT_EXIST'):
            self.client.call_action('update_team', team=team)

    def test_update_team_not_a_member(self):
        team = factories.TeamFactory.create_protobuf(organization_id=self.organization.id)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_team', team=team)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_team_not_a_coordinator(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            role=team_containers.TeamMemberV1.MEMBER,
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_team', team=team.to_protobuf())

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_team_coordinator(self):
        team = self._setup_coordinator()

        updated_name = fuzzy.text()
        updated_description = fuzzy.text()
        team.organization_id = fuzzy.uuid()
        team.name = updated_name
        team.description.value = updated_description
        team.description.by_profile_id = fuzzy.uuid()
        response = self.client.call_action('update_team', team=team)
        updated_team = response.result.team
        self.assertEqual(team.id, updated_team.id)
        self.assertEqual(team.organization_id, updated_team.organization_id)
        self.assertEqual(updated_team.name, updated_name)
        self.assertEqual(updated_team.description.value, updated_description)
        self.assertEqual(updated_team.description.by_profile_id, self.profile.id)

        team = models.Team.objects.get(id=updated_team.id)
        self.verify_containers(updated_team, team.to_protobuf())

    def test_update_team_empty_description_doesnt_set_by_profile_id(self):
        team = self._setup_coordinator(description=None)
        team.name = fuzzy.text()
        response = self.client.call_action('update_team', team=team)
        self.assertFalse(response.result.team.description.value)
        self.assertFalse(response.result.team.description.by_profile_id)

    def test_update_team_new_contact_methods(self):
        contact_methods = [
            mocks.mock_team_contact_method(id=None),
            mocks.mock_team_contact_method(id=None),
        ]
        team = self._setup_coordinator()
        team.contact_methods.extend(contact_methods)

        response = self.client.call_action('update_team', team=team)
        updated_team = response.result.team
        self.assertEqual(len(updated_team.contact_methods), len(contact_methods))
        self.assertEqual(
            models.ContactMethod.objects.filter(team_id=team.id).count(),
            len(contact_methods),
        )
        for contact_method in updated_team.contact_methods:
            self.assertTrue(contact_method.id)

    def test_update_team_new_contact_methods_invalid_values(self):
        contact_methods = [
            mocks.mock_team_contact_method(id=None),
            mocks.mock_team_contact_method(id=None, value=''),
        ]
        team = self._setup_coordinator()
        team.contact_methods.extend(contact_methods)

        with self.assertFieldError('contact_methods[1].value', 'MISSING'):
            self.client.call_action('update_team', team=team)

    def test_update_team_update_contact_methods(self):
        contact_method = mocks.mock_team_contact_method()
        team = self._setup_coordinator(contact_methods=[contact_method])
        team.contact_methods[0].value = fuzzy.text()

        response = self.client.call_action('update_team', team=team)
        updated_team = response.result.team
        self.verify_containers(team.contact_methods[0], updated_team.contact_methods[0])

    def test_update_team_delete_contact_methods(self):
        contact_methods = [
            mocks.mock_team_contact_method(),
            mocks.mock_team_contact_method(),
        ]
        team = self._setup_coordinator(contact_methods=contact_methods)
        removed_method = team.contact_methods.pop(0)
        team.contact_methods[0].value = fuzzy.text()
        new_method = team.contact_methods.add()
        new_method.value = fuzzy.text()

        response = self.client.call_action('update_team', team=team)
        updated_team = response.result.team
        self.assertEqual(len(updated_team.contact_methods), 2)
        for contact_method in updated_team.contact_methods:
            self.assertNotEqual(removed_method.id, contact_method.id)

        self.assertEqual(models.ContactMethod.objects.filter(team_id=team.id).count(), 2)

    def test_update_team_delete_all_contact_methods(self):
        contact_methods = [
            mocks.mock_team_contact_method(),
            mocks.mock_team_contact_method(),
        ]
        team = self._setup_coordinator(contact_methods=contact_methods)
        team.ClearField('contact_methods')

        response = self.client.call_action('update_team', team=team)
        updated_team = response.result.team
        self.assertEqual(len(updated_team.contact_methods), 0)
        self.assertEqual(models.ContactMethod.objects.filter(team_id=team.id).count(), 0)
