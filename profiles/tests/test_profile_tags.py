from protobufs.services.profile import containers_pb2 as profile_containers
import service.control

from services.test import (
    fuzzy,
    TestCase,
)

from .. import (
    factories,
    models,
)


class TestProfileTags(TestCase):

    def setUp(self):
        self.client = service.control.Client('profile', token='test-token')
        self.profile = factories.ProfileFactory.create_protobuf()
        organization_client = service.control.Client('organization', token='test-token')
        response = organization_client.call_action(
            'create_organization',
            organization={
                'name': fuzzy.FuzzyText().fuzz(),
                'domain': fuzzy.FuzzyText(suffix='.com').fuzz(),
            },
        )
        self.assertTrue(response.success)
        self.organization = response.result.organization
        self.tags = factories.TagFactory.build_protobufs(size=4, id=None)

    def test_create_tags_invalid(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action(
                'create_tags',
                organization_id='invalid',
                tags=[factories.TagFactory.build_protobuf()],
            )

    def test_create_tags(self):
        response = self.client.call_action(
            'create_tags',
            organization_id=self.organization.id,
            tags=self.tags,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.tags), len(self.tags))

    def test_create_skills_ignore_duplicates(self):
        tags = factories.TagFactory.create_protobufs(
            size=4,
            organization_id=self.organization.id,
            type=profile_containers.TagV1.SKILL,
        )
        for tag in tags:
            tag.ClearField('id')

        # add an additional tag
        tags.extend(factories.TagFactory.build_protobufs(
            size=2,
            name='deduping',
            id=None,
            type=profile_containers.TagV1.SKILL,
        ))
        response = self.client.call_action(
            'create_tags',
            organization_id=self.organization.id,
            tags=tags,
        )
        self.assertEqual(len(response.result.tags), len(tags) - 1)
        self.assertIn('deduping', [tag.name for tag in response.result.tags])

        response = self.client.call_action(
            'get_tags',
            organization_id=self.organization.id,
        )
        self.assertEqual(len(response.result.tags), len(tags) - 1)
        self.assertIn('deduping', [tag.name for tag in response.result.tags])

    def test_get_tags_for_organization_invalid_organization_id(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_tags', organization_id='invalid')

    def test_get_tags_for_profile_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_tags', profile_id='invalid')

    def test_get_tags_for_organization(self):
        factories.TagFactory.create_protobufs(
            size=4,
            organization_id=self.organization.id,
            type=profile_containers.TagV1.SKILL,
        )
        response = self.client.call_action('get_tags', organization_id=self.organization.id)
        self.assertTrue(response.success)
        self.assertEqual(len(self.tags), len(response.result.tags))

    def test_get_skills_for_organization(self):
        factories.TagFactory.create_protobufs(
            size=4,
            organization_id=self.organization.id,
            type=profile_containers.TagV1.SKILL,
        )
        # create interests which shouldn't be returned
        factories.TagFactory.create_protobufs(
            size=4,
            organization_id=self.organization.id,
            type=profile_containers.TagV1.INTEREST,
        )
        response = self.client.call_action(
            'get_tags',
            organization_id=self.organization.id,
            tag_type=profile_containers.TagV1.SKILL,
        )
        self.assertEqual(len(response.result.tags), 4)

    def test_get_interests_for_organization(self):
        factories.TagFactory.create_protobufs(
            size=4,
            organization_id=self.organization.id,
            type=profile_containers.TagV1.INTEREST,
        )
        # create skills which shouldn't be returned
        factories.TagFactory.create_protobufs(
            size=4,
            organization_id=self.organization.id,
            type=profile_containers.TagV1.SKILL,
        )
        response = self.client.call_action(
            'get_tags',
            organization_id=self.organization.id,
            tag_type=profile_containers.TagV1.INTEREST,
        )
        self.assertEqual(len(response.result.tags), 4)

    def test_add_tags_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'add_tags',
                profile_id='invalid',
                tags=[factories.TagFactory.build_protobuf()],
            )

    def test_add_tags_profile_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'add_tags',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
                tags=[factories.TagFactory.build_protobuf()],
            )

    def test_add_skills(self):
        tags = factories.TagFactory.create_protobufs(
            size=4,
            organization_id=self.organization.id,
            type=profile_containers.TagV1.SKILL,
        )
        response = self.client.call_action(
            'add_tags',
            profile_id=self.profile.id,
            tags=tags[:2],
        )

        response = self.client.call_action('get_tags', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.tags), 2)

    def test_get_tags_for_profile(self):
        tags = factories.TagFactory.create_protobufs(
            size=4,
            organization_id=self.organization.id,
            type=profile_containers.TagV1.SKILL,
        )
        response = self.client.call_action('add_tags', profile_id=self.profile.id, tags=tags)

        response = self.client.call_action('get_tags', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(tags), len(response.result.tags))

    def test_add_skills_duplicate_noop(self):
        tag = factories.TagFactory.create(type=profile_containers.TagV1.SKILL)
        profile = factories.ProfileFactory.create(tags=[tag])
        response = self.client.call_action(
            'add_tags',
            profile_id=str(profile.id),
            tags=[factories.TagFactory.to_protobuf(tag)],
        )
        self.assertTrue(response.success)

        response = self.client.call_action('get_tags', profile_id=str(profile.id))
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.tags), 1)

    def test_add_tags_create_required(self):
        profile = factories.ProfileFactory.create()
        self.client.call_action(
            'add_tags',
            profile_id=str(profile.id),
            tags=[factories.TagFactory.build_protobuf(id=None, type=profile_containers.TagV1.SKILL)],
        )

        response = self.client.call_action('get_tags', profile_id=str(profile.id))
        self.assertEqual(len(response.result.tags), 1)

    def test_remove_tags_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'remove_tags',
                profile_id='invalid',
                tags=[factories.TagFactory.create_protobuf()],
            )

    def test_remove_tags_profile_id_required(self):
        with self.assertFieldError('profile_id', 'MISSING'):
            self.client.call_action(
                'remove_tags',
                tags=[factories.TagFactory.create_protobuf()],
            )

    def test_remove_tags(self):
        tags = factories.TagFactory.create_batch(size=4, organization_id=self.organization.id)
        profile = factories.ProfileFactory.create_protobuf(tags=tags)
        self.client.call_action(
            'remove_tags',
            profile_id=profile.id,
            tags=[factories.TagFactory.to_protobuf(tag) for tag in tags[:2]],
        )
        self.assertEqual(models.ProfileTags.objects.filter(profile_id=profile.id).count(), 2)

    def test_remove_tags_tags_required(self):
        with self.assertFieldError('tags', 'MISSING'):
            self.client.call_action('remove_tags', profile_id=fuzzy.FuzzyUUID().fuzz())
