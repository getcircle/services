import service.control
import unittest

from services.test import (
    fuzzy,
    TestCase,
)

from .. import factories


class TestProfileSkills(TestCase):

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
        self.skills = [{'name': 'python'}, {'name': 'mysql'}, {'name': 'iOS'}, {'name': 'docker'}]

    def _create_skills_for_organization(self, organization_id, skills=None):
        if skills is None:
            skills = [{'name': 'python'}, {'name': 'mysql'}]

        response = self.client.call_action(
            'create_skills',
            organization_id=organization_id,
            skills=skills,
        )
        self.assertTrue(response.success)
        return response.result.skills

    def test_create_skills_invalid(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action(
                'create_skills',
                organization_id='invalid',
                skills=[{'name': 'python'}],
            )

    # TODO i'm unsure whether or not we need to check to see if the organization exists
    #def test_create_skills_does_not_exist(self):
        #response = self.client.call_action(
            #'create_skills',
            #organization_id=fuzzy.FuzzyUUID().fuzz(),
        #)
        #self._verify_field_error(response, 'organization_id', 'DOES_NOT_EXIST')

    def test_create_skills(self):
        response = self.client.call_action(
            'create_skills',
            organization_id=self.organization.id,
            skills=self.skills,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.skills), len(self.skills))

    @unittest.skip(
        'punting on this for now - pushed start of solution to "create-skills-ignore-duplicates"'
    )
    def test_create_skills_ignore_duplicates(self):
        self.client.call_action(
            'create_skills',
            organization_id=self.organization.id,
            skills=self.skills,
        )
        response = self.client.call_action(
            'create_skills',
            organization_id=self.organization.id,
            skills=self.skills,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.skills), len(self.skills))

    def test_get_skills_for_organization_invalid_organization_id(self):
        with self.assertFieldError('organization_id'):
            self.client.call_action('get_skills', organization_id='invalid')

    def test_get_skills_for_profile_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_skills', profile_id='invalid')

    def test_get_skills_for_organization(self):
        self._create_skills_for_organization(self.organization.id, skills=self.skills)
        response = self.client.call_action('get_skills', organization_id=self.organization.id)
        self.assertTrue(response.success)
        self.assertEqual(len(self.skills), len(response.result.skills))

    def test_add_skills_invalid_profile_id(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action(
                'add_skills',
                profile_id='invalid',
                skills=[{'id': fuzzy.FuzzyUUID().fuzz(), 'name': 'mysql'}],
            )

    def test_add_skills_profile_does_not_exist(self):
        with self.assertFieldError('profile_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'add_skills',
                profile_id=fuzzy.FuzzyUUID().fuzz(),
                skills=[{'id': fuzzy.FuzzyUUID().fuzz(), 'name': 'mysql'}],
            )

    def test_add_skills(self):
        skills = self._create_skills_for_organization(self.organization.id, skills=self.skills)
        response = self.client.call_action(
            'add_skills',
            profile_id=self.profile.id,
            skills=skills[:2],
        )
        self.assertTrue(response.success)

        response = self.client.call_action('get_skills', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.skills), 2)

    def test_get_skills_for_profile(self):
        skills = self._create_skills_for_organization(self.organization.id, skills=self.skills)
        response = self.client.call_action('add_skills', profile_id=self.profile.id, skills=skills)

        response = self.client.call_action('get_skills', profile_id=self.profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(skills), len(response.result.skills))

    def test_add_skills_duplicate_noop(self):
        skill = factories.SkillFactory.create()
        profile = factories.ProfileFactory.create(skills=[skill])
        response = self.client.call_action(
            'add_skills',
            profile_id=str(profile.id),
            skills=[factories.SkillFactory.to_protobuf(skill)],
        )
        self.assertTrue(response.success)

        response = self.client.call_action('get_skills', profile_id=str(profile.id))
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.skills), 1)
