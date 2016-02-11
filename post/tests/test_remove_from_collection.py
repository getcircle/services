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

    def _verify_can_remove_from_collection(self, collection):
        collection_item = factories.CollectionItemFactory.create_protobuf(collection=collection)
        self.client.call_action(
            'remove_from_collection',
            collection_id=str(collection.id),
            collection_item_id=collection_item.id,
        )
        self.assertFalse(models.CollectionItem.objects.filter(
            id=collection_item.id,
            collection_id=collection.id,
        ).exists())

    def test_remove_from_collection_collection_id_required(self):
        with self.assertFieldError('collection_id', 'MISSING'):
            self.client.call_action('remove_from_collection')

    def test_remove_from_collection_collection_item_id_required(self):
        with self.assertFieldError('collection_item_id', 'MISSING'):
            self.client.call_action('remove_from_collection', collection_id=fuzzy.uuid())

    def test_remove_from_collection_collection_id_invalid(self):
        with self.assertFieldError('collection_id'):
            self.client.call_action(
                'remove_from_collection',
                collection_id=fuzzy.text(),
                collection_item_id=fuzzy.uuid(),
            )

    def test_remove_from_collection_collection_item_id_invalid(self):
        with self.assertFieldError('collection_item_id'):
            self.client.call_action(
                'remove_from_collection',
                collection_id=fuzzy.uuid(),
                collection_item_id=fuzzy.text(),
            )

    def test_remove_from_collection_collection_id_does_not_exist(self):
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'remove_from_collection',
                collection_id=fuzzy.uuid(),
                collection_item_id=fuzzy.uuid(),
            )

    def test_remove_from_collection_wrong_organization(self):
        collection = factories.CollectionFactory.create_protobuf()
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'remove_from_collection',
                collection_id=collection.id,
                collection_item_id=fuzzy.uuid(),
            )

    def test_remove_from_collection_owned_by_profile_not_your_profile(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'remove_from_collection',
                collection_id=collection.id,
                collection_item_id=fuzzy.uuid(),
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_remove_from_collection_owned_by_profile(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        self._verify_can_remove_from_collection(collection)

    def test_remove_from_collection_collection_item_does_not_exist(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        collection_item_id = fuzzy.uuid()
        self.client.call_action(
            'remove_from_collection',
            collection_id=str(collection.id),
            collection_item_id=collection_item_id,
        )
        self.assertFalse(models.CollectionItem.objects.filter(
            id=collection_item_id,
            collection_id=collection.id,
        ).exists())

    def test_remove_from_collection_owned_by_profile_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create(profile=profile)
        self._verify_can_remove_from_collection(collection)

    def test_remove_from_collection_owned_by_team_not_member(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'remove_from_collection',
                collection_id=collection.id,
                collection_item_id=fuzzy.uuid(),
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_remove_from_collection_owned_by_team_member(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team, role=team_containers.TeamMemberV1.MEMBER)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'remove_from_collection',
                collection_id=collection.id,
                collection_item_id=fuzzy.uuid(),
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_remove_from_collection_owned_by_team_coordinator(self):
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team, role=team_containers.TeamMemberV1.COORDINATOR)
        collection = factories.CollectionFactory.create(team=team)
        self._verify_can_remove_from_collection(collection)

    def test_remove_from_collection_owned_by_team_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team, admin=True)
        collection = factories.CollectionFactory.create(team=team)
        self._verify_can_remove_from_collection(collection)
