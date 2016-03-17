from protobufs.services.team import containers_pb2 as team_containers
from protobufs.services.post import containers_pb2 as post_containers
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
        self.mock.instance.dont_mock_service('post')

    def _setup_coordinator(self, **overrides):
        team = factories.TeamFactory.create(organization_id=self.organization.id, **overrides)
        factories.TeamMemberFactory.create(
            team=team,
            role=team_containers.TeamMemberV1.COORDINATOR,
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        return team.to_protobuf()

    def test_delete_team_team_id_required(self):
        with self.assertFieldError('team_id', 'MISSING'):
            self.client.call_action('delete_team')

    def test_delete_team_team_does_not_exist(self):
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_team', team_id=fuzzy.uuid())

    def test_delete_team_wrong_organization(self):
        team = factories.TeamFactory.create_protobuf()
        with self.assertFieldError('team_id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_team', team_id=team.id)

    def test_delete_team_not_a_coordinator(self):
        team = factories.TeamFactory.create(organization_id=self.organization.id)
        factories.TeamMemberFactory.create(
            team=team,
            role=team_containers.TeamMemberV1.MEMBER,
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_team', team_id=str(team.id))

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_delete_team_as_coordinator(self):
        contact_method = mocks.mock_team_contact_method(id=None)
        team = self._setup_coordinator(contact_methods=[contact_method])
        
        post_client = service.control.Client('post', token=self.token)
        collection = mocks.mock_collection(
            id=None,
            owner_type=post_containers.CollectionV1.TEAM,
            owner_id=team.id,
        )
        create_collection_response = post_client.call_action('create_collection', collection=collection)
        collection = create_collection_response.result.collection

        self.client.call_action('delete_team', team_id=str(team.id))

        self.assertFalse(models.Team.objects.filter(pk=team.id).exists())
        self.assertEqual(models.ContactMethod.objects.filter(team_id=team.id).count(), 0)
        self.assertEqual(models.TeamMember.objects.filter(team_id=team.id).count(), 0)
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            post_client.call_action('get_collection', collection_id=collection.id)
