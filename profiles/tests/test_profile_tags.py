import service.control

from services.test import (
    fuzzy,
    TestCase,
)


class TestProfileTags(TestCase):

    def setUp(self):
        self.client = service.control.Client('profile', token='test-token')
        self.profile_data = {
            'organization_id': fuzzy.FuzzyUUID().fuzz(),
            'user_id': fuzzy.FuzzyUUID().fuzz(),
            'address_id': fuzzy.FuzzyUUID().fuzz(),
            'title': fuzzy.FuzzyText().fuzz(),
            'first_name': fuzzy.FuzzyText().fuzz(),
            'last_name': fuzzy.FuzzyText().fuzz(),
            'cell_phone': fuzzy.FuzzyText().fuzz(),
            'work_phone': '+19492933322',
            'image_url': fuzzy.FuzzyText().fuzz(),
            'email': fuzzy.FuzzyText(suffix='@example.com').fuzz(),
            'team_id': fuzzy.FuzzyUUID().fuzz(),
        }
        response = self.client.call_action('create_profile', profile=self.profile_data)
        self.assertTrue(response.success)
        self.profile = response.result.profile

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
        self.tags = [{'name': 'python'}, {'name': 'mysql'}, {'name': 'iOS'}, {'name': 'docker'}]

    def _create_tags_for_organization(self, organization_id, tags=None):
        if tags is None:
            tags = [{'name': 'python'}, {'name': 'mysql'}]

        response = self.client.call_action(
            'create_tags',
            organization_id=organization_id,
            tags=tags,
        )
        self.assertTrue(response.success)
        return response.result.tags

    def test_create_tags_invalid(self):
        response = self.client.call_action(
            'create_tags',
            organization_id='invalid',
            tags=[{'name': 'python'}],
        )
        self._verify_field_error(response, 'organization_id')

    # TODO i'm unsure whether or not we need to check to see if the organization exists
    #def test_create_tags_does_not_exist(self):
        #response = self.client.call_action(
            #'create_tags',
            #organization_id=fuzzy.FuzzyUUID().fuzz(),
        #)
        #self._verify_field_error(response, 'organization_id', 'DOES_NOT_EXIST')

    def test_create_tags(self):
        response = self.client.call_action(
            'create_tags',
            organization_id=self.organization.id,
            tags=self.tags,
        )
        self.assertTrue(response.success)

    def test_get_tags_for_organization_invalid_organization_id(self):
        response = self.client.call_action('get_tags', organization_id='invalid')
        self._verify_field_error(response, 'organization_id')

    def test_get_tags_for_profile_invalid_profile_id(self):
        response = self.client.call_action('get_tags', profile_id='invalid')
        self._verify_field_error(response, 'profile_id')

    def test_get_tags_for_organization(self):
        self._create_tags_for_organization(self.organization.id, tags=self.tags)
        response = self.client.call_action('get_tags', organization_id=self.organization.id)
        self.assertTrue(response.success)
        self.assertEqual(len(self.tags), len(response.result.tags))

    def test_add_tags_invalid_profile_id(self):
        response = self.client.call_action(
            'add_tags',
            profile_id='invalid',
            tag_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        self._verify_field_error(response, 'profile_id')

    def test_add_tags_profile_does_not_exist(self):
        response = self.client.call_action(
            'add_tags',
            profile_id=fuzzy.FuzzyUUID().fuzz(),
            tag_ids=[fuzzy.FuzzyUUID().fuzz()],
        )
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_add_tags(self):
        tags = self._create_tags_for_organization(self.organization.id, tags=self.tags)
        tag_ids = [tag.id for tag in tags]
        response = self.client.call_action('add_tags', profile_id=self.profile.id, tag_ids=tag_ids)
        self.assertTrue(response.success)

        response = self.client.call_action('get_tags', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(tag_ids), len(response.result.tags))

    def test_get_tags_for_profile(self):
        tags = self._create_tags_for_organization(self.organization.id, tags=self.tags)
        tag_ids = [tag.id for tag in tags]
        response = self.client.call_action('add_tags', profile_id=self.profile.id, tag_ids=tag_ids)

        response = self.client.call_action('get_tags', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(tag_ids), len(response.result.tags))
