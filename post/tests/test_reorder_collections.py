from protobufs.services.post import containers_pb2 as post_containers
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

    return post_containers.PositionDiffV1(
        item_id=item_id,
        current_position=current_position,
        new_position=new_position,
    )


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

        factories.CollectionFactory.reset_sequence()

    def _verify_can_reorder_collections(self, owner_id=None, owner_type=None):
        collections = factories.CollectionFactory.create_protobufs(
            size=10,
            organization_id=self.organization.id,
            by_profile_id=self.profile.id,
            owner_type=owner_type if owner_type else post_containers.CollectionV1.PROFILE,
            owner_id=owner_id if owner_id else self.profile.id,
        )
        # move the last item to the top of the list
        collection = collections[-1]
        self.client.call_action(
            'reorder_collections',
            diffs=[mock_position_diff(
                item_id=collection.id,
                current_position=collection.position,
                new_position=0,
            )],
        )

        instances = models.Collection.objects.filter(
            organization_id=self.organization.id,
            by_profile_id=self.profile.id,
            owner_type=owner_type if owner_type else post_containers.CollectionV1.PROFILE,
            owner_id=owner_id if owner_id else self.profile.id,
        ).order_by('position')
        collections_by_id = dict((str(collection.id), collection) for collection in instances)

        # verify all the original collections were resorted
        for index, collection in enumerate(collections):
            updated_collection = collections_by_id[collection.id]
            if index == len(collections) - 1:
                # this should now be the first collection
                self.assertEqual(updated_collection.position, 0)
            else:
                # otherwise index should have been bumped by 1
                self.assertEqual(updated_collection.position, collection.position + 1)

    def test_reorder_collections_diffs_required(self):
        with self.assertFieldError('diffs', 'MISSING'):
            self.client.call_action('reorder_collections')

    def test_reorder_collections_collection_id_invalid(self):
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'reorder_collections',
                diffs=[mock_position_diff()],
            )

    def test_reorder_collections_collection_id_does_not_exist(self):
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'reorder_collections',
                diffs=[mock_position_diff(item_id=fuzzy.uuid())],
            )

    def test_reorder_collections_collection_id_wrong_organization(self):
        collection = factories.CollectionFactory.create_protobuf()
        with self.assertFieldError('collection_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'reorder_collections',
                diffs=[mock_position_diff(item_id=collection.id)],
            )

    def test_reorder_collections_owned_by_profile_not_your_profile(self):
        self.profile.is_admin = False
        mock_get_profile(self.mock.instance, self.profile)
        profile = mocks.mock_profile(organization_id=self.organization.id)
        collection = factories.CollectionFactory.create_protobuf(profile=profile)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'reorder_collections',
                diffs=[mock_position_diff(item_id=collection.id)],
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_reorder_collections_owned_by_profile_admin(self):
        self.profile.is_admin = True
        mock_get_profile(self.mock.instance, self.profile)
        profile = mocks.mock_profile(organization_id=self.organization.id)
        self._verify_can_reorder_collections(owner_id=profile.id, owner_type=post_containers.CollectionV1.PROFILE)

    def test_reorder_collections_owned_by_team_not_member(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team])
        mock_get_profile(self.mock.instance, self.profile)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'reorder_collections',
                diffs=[mock_position_diff(item_id=collection.id)],
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_reorder_collections_owned_by_team_member(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], role=team_containers.TeamMemberV1.MEMBER)
        mock_get_profile(self.mock.instance, self.profile)
        collection = factories.CollectionFactory.create_protobuf(team=team)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action(
                'reorder_collections',
                diffs=[mock_position_diff(item_id=collection.id)],
            )

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_reorder_collections_owned_by_team_coordinator(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], role=team_containers.TeamMemberV1.COORDINATOR)
        mock_get_profile(self.mock.instance, self.profile)
        self._verify_can_reorder_collections(owner_id=team.id, owner_type=post_containers.CollectionV1.TEAM)

    def test_reorder_collections_owned_by_team_admin(self):
        self.profile.is_admin = True
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_teams(self.mock.instance, [team], admin=True)
        mock_get_profile(self.mock.instance, self.profile)
        self._verify_can_reorder_collections(owner_id=team.id, owner_type=post_containers.CollectionV1.TEAM)

    def test_reorder_collections_owned_by_profile(self):
        self._verify_can_reorder_collections()

    def test_reorder_collections_reorder_multiple_collections(self):
        collections = factories.CollectionFactory.create_protobufs(
            size=10,
            organization_id=self.organization.id,
            by_profile_id=self.profile.id,
            owner_type=post_containers.CollectionV1.PROFILE,
            owner_id=self.profile.id,
        )

        diffs = []
        # move the last collection up one
        collection = collections[-1]
        diffs.append(mock_position_diff(
            item_id=collection.id,
            current_position=collection.position,
            new_position=collection.position - 1,
        ))

        # move the 3rd collection down one
        collection = collections[2]
        diffs.append(mock_position_diff(
            item_id=collection.id,
            current_position=collection.position,
            new_position=collection.position + 1,
        ))

        # move the 5th collection down two
        collection = collections[4]
        diffs.append(mock_position_diff(
            item_id=collection.id,
            current_position=collection.position,
            new_position=collection.position + 2,
        ))

        self.client.call_action(
            'reorder_collections',
            diffs=diffs,
        )

        instances = models.Collection.objects.filter(
            organization_id=self.organization.id,
            by_profile_id=self.profile.id,
            owner_type=post_containers.CollectionV1.PROFILE,
            owner_id=self.profile.id,
        ).order_by('position')
        collections_by_id = dict((str(collection.id), collection) for collection in instances)

        # verify all the original collections were resorted
        for index, collection in enumerate(collections):
            updated_collection = collections_by_id[collection.id]
            if index == len(collections) - 1:
                # this should now be the second to last collection
                self.assertEqual(updated_collection.position, 8)
            elif index == len(collections) - 2:
                # this should now be the last collection
                self.assertEqual(updated_collection.position, 9)
            elif index == 2:
                self.assertEqual(updated_collection.position, 3)
            elif index == 4:
                self.assertEqual(updated_collection.position, 6)
            elif index < 2:
                # these should not have changed
                self.assertEqual(updated_collection.position, collection.position)
            elif index == 3:
                # this should have moved up 1
                self.assertEqual(updated_collection.position, 2)
            elif index == 5:
                # should have moved up 1
                self.assertEqual(updated_collection.position, 4)
            elif index == 6:
                self.assertEqual(updated_collection.position, 5)
