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

from .helpers import (
    mock_get_profile,
    mock_get_teams,
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

        factories.CollectionItemFactory.reset_sequence()

    def _verify_can_update_collection(self, collection):
        collection.name = fuzzy.text()
        response = self.client.call_action(
            'update_collection',
            collection=collection,
        )
        updated_collection = response.result.collection
        self.verify_containers(collection, response.result.collection, ignore_fields=['changed'])
        instance = models.Collection.objects.get(id=updated_collection.id)
        self.verify_containers(updated_collection, instance.to_protobuf())

    def test_update_collection_collection_required(self):
        with self.assertFieldError('collection', 'MISSING'):
            self.client.call_action('update_collection')

    def test_update_collection_collection_id_invalid(self):
        with self.assertFieldError('collection.id'):
            self.client.call_action(
                'update_collection',
                collection={'id': fuzzy.text(), 'name': fuzzy.text()},
            )

    def test_update_collection_collection_id_does_not_exist(self):
        with self.assertFieldError('collection.id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'update_collection',
                collection=mocks.mock_collection(organization_id=self.organization.id),
            )

    def test_update_collection_wrong_organization(self):
        collection = factories.CollectionFactory.create_protobuf()
        with self.assertFieldError('collection.id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'update_collection',
                collection=collection,
            )

    def test_update_collection_owned_by_profile_not_your_profile(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'update_collection',
                collection=collection,
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_collection_owned_by_profile(self):
        collection = factories.CollectionFactory.create_protobuf(profile=self.profile)
        self._verify_can_update_collection(collection)

    def test_update_collection_name_required(self):
        collection = factories.CollectionFactory.create_protobuf(profile=self.profile)
        collection.ClearField('name')
        with self.assertFieldError('collection.name', 'MISSING'):
            self.client.call_action('update_collection', collection=collection)

    def test_update_collection_ignore_fields(self):
        collection = factories.CollectionFactory.create_protobuf(profile=self.profile)

        # fields we should ignore
        collection.owner_type = post_containers.CollectionV1.TEAM
        collection.owner_id = fuzzy.uuid()
        collection.organization_id = fuzzy.uuid()
        collection.is_default = True
        collection.by_profile_id = fuzzy.uuid()
        collection.name = fuzzy.text()

        response = self.client.call_action('update_collection', collection=collection)
        updated_collection = response.result.collection
        self.assertNotEqual(updated_collection.owner_type, collection.owner_type)
        self.assertNotEqual(updated_collection.owner_id, collection.owner_id)
        self.assertNotEqual(updated_collection.organization_id, collection.organization_id)
        self.assertNotEqual(updated_collection.is_default, collection.is_default)
        self.assertNotEqual(updated_collection.by_profile_id, collection.by_profile_id)
        self.assertEqual(updated_collection.name, collection.name)

    def test_update_collection_owned_by_profile_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        self._verify_can_update_collection(collection)

    def test_update_collection_owned_by_team_not_member(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team])
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_collection', collection=collection)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_collection_owned_by_team_member(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], role=team_containers.TeamMemberV1.MEMBER)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('update_collection', collection=collection)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_update_collection_owned_by_team_coordinator(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], role=team_containers.TeamMemberV1.COORDINATOR)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        self._verify_can_update_collection(collection)

    def test_update_collection_owned_by_team_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], admin=True)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        self._verify_can_update_collection(collection)
