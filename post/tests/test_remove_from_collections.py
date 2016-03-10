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

from .helpers import (
    mock_get_profile,
    mock_get_team,
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

    def _verify_can_remove_from_collections(self, collections):
        source_id = fuzzy.uuid()
        for collection in collections:
            factories.CollectionItemFactory.create_protobuf(collection=collection)

        self.client.call_action(
            'remove_from_collections',
            item={'source_id': source_id},
            collections=[c.to_protobuf() for c in collections],
        )
        self.assertFalse(models.CollectionItem.objects.filter(
            source_id=source_id,
            collection_id=collection.id,
        ).exists())

    def test_remove_from_collections_item_required(self):
        with self.assertFieldError('item', 'MISSING'):
            self.client.call_action('remove_from_collections')

    def test_remove_from_collections_collections_required(self):
        with self.assertFieldError('collections', 'MISSING'):
            self.client.call_action(
                'remove_from_collections',
                item=mocks.mock_collection_item(),
            )

    def test_remove_from_collections_wrong_organization(self):
        collection = factories.CollectionFactory.create()
        item = factories.CollectionItemFactory.create_protobuf(collection=collection)
        self.client.call_action(
            'remove_from_collections',
            collections=[collection.to_protobuf()],
            item=item,
        )
        self.assertTrue(models.CollectionItem.objects.filter(id=item.id).exists())

    def test_remove_from_collections_owned_by_profile_not_your_profile(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create(profile=profile)
        item = factories.CollectionItemFactory.create_protobuf(collection=collection)
        self.client.call_action(
            'remove_from_collections',
            collections=[collection.to_protobuf()],
            item=item,
        )

        self.assertTrue(models.CollectionItem.objects.filter(id=item.id).exists())

    def test_remove_from_collections_owned_by_profile(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        self._verify_can_remove_from_collections([collection])

    def test_remove_from_collections_owned_by_profile_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create(profile=profile)
        self._verify_can_remove_from_collections([collection])

    def test_remove_from_collections_owned_by_team_not_member(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team)
        collection = factories.CollectionFactory.create(team=team)
        item = factories.CollectionItemFactory.create_protobuf(collection=collection)
        self.client.call_action(
            'remove_from_collections',
            item=item,
            collections=[collection.to_protobuf()],
        )
        self.assertTrue(models.CollectionItem.objects.filter(id=item.id).exists())

    def test_remove_from_collections_owned_by_team_member(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team, role=team_containers.TeamMemberV1.MEMBER)
        collection = factories.CollectionFactory.create(team=team)
        item = factories.CollectionItemFactory.create_protobuf(collection=collection)
        self.client.call_action(
            'remove_from_collections',
            item=item,
            collections=[collection.to_protobuf()],
        )
        self.assertTrue(models.CollectionItem.objects.filter(id=item.id).exists())

    def test_remove_from_collections_owned_by_team_coordinator(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team, role=team_containers.TeamMemberV1.COORDINATOR)
        collection = factories.CollectionFactory.create(team=team)
        self._verify_can_remove_from_collections([collection])

    def test_remove_from_collections_owned_by_team_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team, admin=True)
        collection = factories.CollectionFactory.create(team=team)
        self._verify_can_remove_from_collections([collection])

    def test_remove_from_collections_reorder_items(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        items = factories.CollectionItemFactory.create_protobufs(size=5, collection=collection)
        self.client.call_action(
            'remove_from_collections',
            item=items[2],
            collections=[collection.to_protobuf()],
        )
        self.assertEqual(
            models.CollectionItem.objects.filter(collection_id=collection.id).count(),
            len(items) - 1,
        )
        verify_items = models.CollectionItem.objects.filter(collection_id=collection.id).order_by(
            'position'
        )
        self.assertEqual(len(verify_items), len(items) - 1)
        for index, item in enumerate(verify_items):
            self.assertEqual(index, item.position)
