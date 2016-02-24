from protobufs.services.team import containers_pb2 as team_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories

from .helpers import mock_get_team


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.team = mocks.mock_team(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

        factories.CollectionItemFactory.reset_sequence()

    def _verify_permissions(self, response, full_access):
        permissions = response.result.collection.permissions
        self.assertEqual(permissions.can_edit, full_access)
        self.assertEqual(permissions.can_delete, full_access)
        self.assertEqual(permissions.can_add, full_access)

    def test_get_collection_collection_id_invalid(self):
        with self.assertFieldError('collection_id'):
            self.client.call_action('get_collection', collection_id=fuzzy.text())

    def test_get_collection_owned_by_team_wrong_organization(self):
        team = mocks.mock_team()
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_collection', collection_id=collection.id)

    def test_get_collection_owned_by_profile_wrong_organization(self):
        profile = mocks.mock_profile()
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_collection', collection_id=collection.id)

    def test_get_collection_owned_by_team(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        response = self.client.call_action('get_collection', collection_id=collection.id)
        self.verify_containers(collection, response.result.collection)

        self._verify_permissions(response, False)

    def test_get_collection_owned_by_team_inflate_posts(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create(team=team)
        factories.CollectionItemFactory.create_batch(
            size=10,
            collection=collection,
        )

        response = self.client.call_action(
            'get_collection',
            collection_id=str(collection.id),
            fields={'only': ['name']},
        )
        response_collection = response.result.collection
        self.assertEqual(collection.name, response_collection.name)
        self.assertFalse(response_collection.created)
        self.assertEqual(response_collection.total_items, 10)

    def test_get_collection_owned_by_profile_not_your_profile(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        response = self.client.call_action('get_collection', collection_id=collection.id)
        self.verify_containers(collection, response.result.collection)
        self._verify_permissions(response, False)

    def test_get_collection_owned_by_profile(self):
        collection = factories.CollectionFactory.create_protobuf(profile=self.profile)
        response = self.client.call_action('get_collection', collection_id=collection.id)
        self.verify_containers(collection, response.result.collection)
        self._verify_permissions(response, True)

    def test_get_collection_owned_by_profile_is_default(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile, is_default=True)
        response = self.client.call_action('get_collection', collection_id=collection.id)
        self.verify_containers(collection, response.result.collection)
        self.assertTrue(response.result.collection.is_default)

    def test_get_collection_owned_by_team_not_member(self):
        mock_get_team(self.mock.instance, self.team)
        collection = factories.CollectionFactory.create_protobuf(team=self.team)
        response = self.client.call_action('get_collection', collection_id=collection.id)
        self.verify_containers(collection, response.result.collection)
        self._verify_permissions(response, False)

    def test_get_collection_owned_by_team_member(self):
        mock_get_team(self.mock.instance, self.team, role=team_containers.TeamMemberV1.MEMBER)
        collection = factories.CollectionFactory.create_protobuf(team=self.team)
        response = self.client.call_action('get_collection', collection_id=collection.id)
        self.verify_containers(collection, response.result.collection)
        self._verify_permissions(response, False)

    def test_get_collection_owned_by_team_coordinator(self):
        mock_get_team(self.mock.instance, self.team, role=team_containers.TeamMemberV1.COORDINATOR)
        collection = factories.CollectionFactory.create_protobuf(team=self.team)
        response = self.client.call_action('get_collection', collection_id=collection.id)
        self.verify_containers(collection, response.result.collection)
        self._verify_permissions(response, True)

    def test_get_collection_owned_by_profile_not_your_profile_admin(self):
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

        response = self.client.call_action('get_collection', collection_id=collection.id)
        self.verify_containers(collection, response.result.collection)
        self._verify_permissions(response, True)
