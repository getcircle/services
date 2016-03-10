from protobufs.services.team import containers_pb2 as team_containers
from protobufs.services.post import containers_pb2 as post_containers
import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import (
    models,
)

from .helpers import (
    mock_get_team,
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

    def test_create_collection_collection_required(self):
        with self.assertFieldError('collection', 'MISSING'):
            self.client.call_action('create_collection')

    def test_create_collection_collection_name_required(self):
        with self.assertFieldError('collection.name', 'MISSING'):
            self.client.call_action(
                'create_collection',
                collection={'created': fuzzy.text()},
            )

    def test_create_collection_ignore_fields(self):
        collection = mocks.mock_collection(created='random', changed='random')
        response = self.client.call_action('create_collection', collection=collection)
        new_collection = response.result.collection
        self.assertNotEqual(collection.id, new_collection.id)
        self.assertNotEqual(collection.changed, new_collection.changed)
        self.assertNotEqual(collection.created, new_collection.created)

    def test_create_collection_for_team_coordinator(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team, role=team_containers.TeamMemberV1.COORDINATOR)
        mock_get_teams(
            self.mock.instance,
            [team],
            inflations={'disabled': True},
            fields={'only': ['id', 'name']},
        )
        collection = mocks.mock_collection(
            id=None,
            owner_type=post_containers.CollectionV1.TEAM,
            owner_id=team.id,
        )
        response = self.client.call_action('create_collection', collection=collection)
        new_collection = response.result.collection
        self.assertEqual(
            new_collection.by_profile_id,
            self.profile.id,
            'Should track by_profile_id for team collections',
        )
        self.assertEqual(new_collection.organization_id, self.organization.id)
        self.assertEqual(new_collection.owner_type, post_containers.CollectionV1.TEAM)
        self.assertEqual(new_collection.owner_id, collection.owner_id)
        self.assertEqual(new_collection.display_name, '[%s] %s' % (team.name, new_collection.name))

    def test_create_collection_for_profile(self):
        collection = mocks.mock_collection(
            id=None,
            owner_type=post_containers.CollectionV1.PROFILE,
            owner_id=fuzzy.uuid(),
        )
        response = self.client.call_action('create_collection', collection=collection)
        new_collection = response.result.collection
        self.assertFalse(
            new_collection.by_profile_id,
            'Shouldn\'t track by_profile_id for profile collections',
        )
        self.assertEqual(new_collection.owner_id, self.profile.id)
        self.assertEqual(new_collection.organization_id, self.organization.id)
        self.assertEqual(new_collection.owner_type, post_containers.CollectionV1.PROFILE)

    def test_create_collection_cant_set_is_default(self):
        collection = mocks.mock_collection(id=None, is_default=True)
        response = self.client.call_action('create_collection', collection=collection)
        new_collection = response.result.collection
        self.assertFalse(new_collection.is_default)

    def test_create_collection_for_team_not_member(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team)
        collection = mocks.mock_collection(
            id=None,
            owner_type=post_containers.CollectionV1.TEAM,
            owner_id=team.id,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('create_collection', collection=collection)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_create_collection_for_team_member(self):
        team = mocks.mock_team(organization_id=self.organization.id)
        mock_get_team(self.mock.instance, team, role=team_containers.TeamMemberV1.MEMBER)
        collection = mocks.mock_collection(
            id=None,
            owner_type=post_containers.CollectionV1.TEAM,
            owner_id=team.id,
        )
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('create_collection', collection=collection)

        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_create_collection_reorder_collections(self):
        response = self.client.call_action(
            'create_collection',
            collection=mocks.mock_collection(
                id=None,
                owner_type=post_containers.CollectionV1.PROFILE,
                owner_id=fuzzy.uuid(),
            ),
        )
        first_collection = response.result.collection
        self.assertEqual(0, first_collection.position)

        response = self.client.call_action(
            'create_collection',
            collection=mocks.mock_collection(
                id=None,
                owner_type=post_containers.CollectionV1.PROFILE,
                owner_id=fuzzy.uuid(),
            ),
        )
        second_collection = response.result.collection
        self.assertEqual(0, second_collection.position)
        first_collection = models.Collection.objects.get(pk=first_collection.id)
        self.assertEqual(1, first_collection.position)

        response = self.client.call_action(
            'create_collection',
            collection=mocks.mock_collection(
                id=None,
                owner_type=post_containers.CollectionV1.PROFILE,
                owner_id=fuzzy.uuid(),
            ),
        )
        third_collection = response.result.collection
        self.assertEqual(0, third_collection.position)
        second_collection = models.Collection.objects.get(pk=second_collection.id)
        self.assertEqual(1, second_collection.position)
        first_collection = models.Collection.objects.get(pk=first_collection.id)
        self.assertEqual(2, first_collection.position)
