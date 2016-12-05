from protobufs.services.post.containers_pb2 import PositionDiffV1
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
    mock_get_teams,
    mock_get_profile,
)


def mock_position_diff(item_id=None, current_position=0, new_position=1):
    if item_id is None:
        item_id = fuzzy.uuid()

    return PositionDiffV1(
        item_id=item_id,
        current_position=current_position,
        new_position=new_position,
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

    def _verify_can_reorder_items(self, collection):
        items = factories.CollectionItemFactory.create_protobufs(size=10, collection=collection)

        # move the last item to the top of the list
        item = items[-1]
        self.client.call_action(
            'reorder_collection',
            collection_id=str(collection.id),
            diffs=[mock_position_diff(
                item_id=item.id,
                current_position=item.position,
                new_position=0,
            )],
        )

        instances = models.CollectionItem.objects.filter(
            collection_id=collection.id,
        ).order_by('position')
        instance_id_to_dict = dict((str(item.id), item) for item in instances)

        # verify all the original items were resorted
        for index, item in enumerate(items):
            updated_item = instance_id_to_dict[item.id]
            if index == len(items) - 1:
                # this should now be the first item
                self.assertEqual(updated_item.position, 0)
            else:
                # otherwise index should have been bumped by 1
                self.assertEqual(updated_item.position, item.position + 1)

    def test_reorder_collection_collection_id_required(self):
        with self.assertFieldError('collection_id', 'MISSING'):
            self.client.call_action('reorder_collection')

    def test_reorder_collection_diffs_required(self):
        with self.assertFieldError('diffs', 'MISSING'):
            self.client.call_action('reorder_collection', collection_id=fuzzy.uuid())

    def test_reorder_collection_collection_id_invalid(self):
        with self.assertFieldError('collection_id'):
            self.client.call_action(
                'reorder_collection',
                collection_id=fuzzy.text(),
                diffs=[mock_position_diff()],
            )

    def test_reorder_collection_collection_id_does_not_exist(self):
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'reorder_collection',
                collection_id=fuzzy.uuid(),
                diffs=[mock_position_diff()],
            )

    def test_reorder_collection_collection_id_wrong_organization(self):
        collection = factories.CollectionFactory.create_protobuf()
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'reorder_collection',
                collection_id=collection.id,
                diffs=[mock_position_diff()],
            )

    def test_reorder_collection_owned_by_profile_not_your_profile(self):
        self.profile.is_admin = False
        mock_get_profile(self.mock.instance, self.profile)
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'reorder_collection',
                collection_id=collection.id,
                diffs=[mock_position_diff()],
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_reorder_collection_owned_by_profile_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create(profile=profile)
        self._verify_can_reorder_items(collection)

    def test_reorder_collection_owned_by_team_not_member(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team])
        mock_get_profile(self.mock.instance, self.profile)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'reorder_collection',
                collection_id=collection.id,
                diffs=[mock_position_diff()],
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_reorder_collection_owned_by_team_member(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], role=team_containers.TeamMemberV1.MEMBER)
        mock_get_profile(self.mock.instance, self.profile)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'reorder_collection',
                collection_id=collection.id,
                diffs=[mock_position_diff()],
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_reorder_collection_owned_by_team_coordinator(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], role=team_containers.TeamMemberV1.COORDINATOR)
        mock_get_profile(self.mock.instance, self.profile)
        collection = factories.CollectionFactory.create(team=team)
        self._verify_can_reorder_items(collection)

    def test_reorder_collection_owned_by_team_admin(self):
        self.profile.is_admin = True
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], admin=True)
        mock_get_profile(self.mock.instance, self.profile)
        collection = factories.CollectionFactory.create(team=team)
        self._verify_can_reorder_items(collection)

    def test_reorder_collection_owned_by_profile(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        self._verify_can_reorder_items(collection)

    def test_reorder_collection_reorder_multiple_items(self):
        collection = factories.CollectionFactory.create(profile=self.profile)
        items = factories.CollectionItemFactory.create_protobufs(size=10, collection=collection)

        diffs = []
        # move the last item up one
        item = items[-1]
        diffs.append(mock_position_diff(
            item_id=item.id,
            current_position=item.position,
            new_position=item.position - 1,
        ))

        # move the 3rd item down one
        item = items[2]
        diffs.append(mock_position_diff(
            item_id=item.id,
            current_position=item.position,
            new_position=item.position + 1,
        ))

        # move the 5th item down two
        item = items[4]
        diffs.append(mock_position_diff(
            item_id=item.id,
            current_position=item.position,
            new_position=item.position + 2,
        ))

        self.client.call_action(
            'reorder_collection',
            collection_id=str(collection.id),
            diffs=diffs,
        )

        instances = models.CollectionItem.objects.filter(
            collection_id=collection.id,
        ).order_by('position')
        instance_id_to_dict = dict((str(item.id), item) for item in instances)

        # verify all the original items were resorted
        for index, item in enumerate(items):
            updated_item = instance_id_to_dict[item.id]
            if index == len(items) - 1:
                # this should now be the second to last item
                self.assertEqual(updated_item.position, 8)
            elif index == len(items) - 2:
                # this should now be the last item
                self.assertEqual(updated_item.position, 9)
            elif index == 2:
                self.assertEqual(updated_item.position, 3)
            elif index == 4:
                self.assertEqual(updated_item.position, 6)
            elif index < 2:
                # these should not have changed
                self.assertEqual(updated_item.position, item.position)
            elif index == 3:
                # this should have moved up 1
                self.assertEqual(updated_item.position, 2)
            elif index == 5:
                # should have moved up 1
                self.assertEqual(updated_item.position, 4)
            elif index == 6:
                self.assertEqual(updated_item.position, 5)
