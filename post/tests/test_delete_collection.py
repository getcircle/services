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
        self.team = mocks.mock_team(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

    def _mock_get_team(self, team, role=None):
        if role == team_containers.TeamMemberV1.COORDINATOR:
            team.permissions.can_edit = True
            team.permissions.can_add = True
            team.permissions.can_delete = True
        elif role is not None:
            team.permissions.can_add = True

        self.mock.instance.register_mock_object(
            service='team',
            action='get_team',
            return_object=team,
            return_object_path='team',
            team_id=team.id,
            fields={'only': ['permissions']},
        )

    def test_delete_collection_collection_id_required(self):
        with self.assertFieldError('collection_id', 'MISSING'):
            self.client.call_action('delete_collection')

    def test_delete_collection_collection_id_does_not_exist(self):
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_collection', collection_id=fuzzy.uuid())

    def test_delete_collection_wrong_organization(self):
        collection = factories.CollectionFactory.create_protobuf()
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_collection', collection_id=collection.id)

    def test_delete_collection_owned_by_team_not_member(self):
        self._mock_get_team(self.team)
        collection = factories.CollectionFactory.create_protobuf(team=self.team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_collection', collection_id=collection.id)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_delete_collection_owned_by_team_member(self):
        self._mock_get_team(self.team, role=team_containers.TeamMemberV1.MEMBER)
        collection = factories.CollectionFactory.create_protobuf(team=self.team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_collection', collection_id=collection.id)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_delete_collection_owned_by_team_coordinator(self):
        self._mock_get_team(self.team, role=team_containers.TeamMemberV1.COORDINATOR)
        collection = factories.CollectionFactory.create_protobuf(team=self.team)
        self.client.call_action('delete_collection', collection_id=collection.id)
        self.assertFalse(models.Collection.objects.filter(pk=collection.id).exists())

    def test_delete_collection_owned_by_profile_not_your_profile(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_collection', collection_id=collection.id)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_delete_collection_owned_by_profile_not_your_profile_admin(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        self.profile.is_admin = True
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object=self.profile,
            return_object_path='profile',
            profile_id=self.profile.id,
            fields={'only': ['is_admin']},
        )

        self.client.call_action('delete_collection', collection_id=collection.id)
        self.assertFalse(models.Collection.objects.filter(pk=collection.id).exists())

    def test_delete_collection_owned_by_profile(self):
        collection = factories.CollectionFactory.create_protobuf(profile=self.profile)
        self.client.call_action('delete_collection', collection_id=collection.id)
        self.assertFalse(models.Collection.objects.filter(pk=collection.id).exists())
