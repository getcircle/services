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

    def _verify_can_add_to_collections(self, collections):
        source_id = fuzzy.uuid()
        response = self.client.call_action(
            'add_to_collections',
            collections=collections,
            item={'source_id': source_id},
        )
        self.assertEqual(len(response.result.items), len(collections))
        for index, item in enumerate(response.result.items):
            self.assertTrue(item.position < len(collections))
            self.assertTrue(item.id)
            self.assertEqual(item.source_id, source_id)
            self.assertEqual(item.by_profile_id, self.profile.id)

            self.assertTrue(models.CollectionItem.objects.filter(
                source_id=source_id,
                collection_id=item.collection_id,
                source=post_containers.CollectionItemV1.LUNO,
            ).exists())

    def test_add_to_collections_item_required(self):
        with self.assertFieldError('item', 'MISSING'):
            self.client.call_action('add_to_collections', collections=[mocks.mock_collection()])

    def test_add_to_collections_collections_required(self):
        with self.assertFieldError('collections', 'MISSING'):
            self.client.call_action('add_to_collections', item=mocks.mock_collection_item())

    def test_add_to_collections_wrong_organization(self):
        collection = factories.CollectionFactory.create_protobuf()
        response = self.client.call_action(
            'add_to_collections',
            item=mocks.mock_collection_item(),
            collections=[collection],
        )
        self.assertFalse(response.result.items)

    def test_add_to_collections_owned_by_profile_not_your_profile(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        response = self.client.call_action(
            'add_to_collections',
            item=mocks.mock_collection_item(),
            collections=[collection],
        )
        self.assertFalse(response.result.items)

    def test_add_to_collections_owned_by_profile(self):
        collections = factories.CollectionFactory.create_protobufs(size=2, profile=self.profile)
        self._verify_can_add_to_collections(collections)

    def test_add_to_collections_owned_by_profile_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collections = factories.CollectionFactory.create_protobufs(size=2, profile=profile)
        self._verify_can_add_to_collections(collections)

    def test_add_to_collections_owned_by_team_not_member(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team])
        collections = factories.CollectionFactory.create_protobufs(size=2, team=team)
        response = self.client.call_action(
            'add_to_collections',
            collections=collections,
            item={'source_id': fuzzy.uuid()},
        )
        self.assertFalse(response.result.items)

    def test_add_to_collections_owned_by_team_member(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], role=team_containers.TeamMemberV1.MEMBER)
        collections = factories.CollectionFactory.create_protobufs(size=2, team=team)
        response = self.client.call_action(
            'add_to_collections',
            collections=collections,
            item={'source_id': fuzzy.uuid()},
        )
        self.assertFalse(response.result.items)

    def test_add_to_collections_owned_by_team_coordinator(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], role=team_containers.TeamMemberV1.COORDINATOR)
        collections = factories.CollectionFactory.create_protobufs(size=2, team=team)
        self._verify_can_add_to_collections(collections)

    def test_add_to_collections_owned_by_team_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], admin=True)
        collections = factories.CollectionFactory.create_protobufs(size=2, team=team)
        self._verify_can_add_to_collections(collections)

    def test_add_to_collections_gets_last_position(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        factories.CollectionItemFactory.create_batch(size=10, collection=collection)
        response = self.client.call_action(
            'add_to_collections',
            collections=[collection.to_protobuf()],
            item={'source_id': fuzzy.uuid()},
        )
        item = response.result.items[0]
        self.assertEqual(item.position, 10)
