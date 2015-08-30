import os
import unittest

from mock import patch
import service.control

from services.token import make_admin_token
from services.test import (
    mocks,
    TestCase,
)

from .parsers.organizations import Parser


@unittest.skip
class TestParser(TestCase):

    def setUp(self):
        self.profile = mocks.mock_profile()
        client = service.control.Client('organization', token=make_admin_token())
        response = client.call_action(
            'create_organization',
            organization={
                'name': 'RH Labs Inc.',
                'domain': 'rhlabs.com',
            },
        )
        self.assertTrue(response.success)
        self.organization = response.result.organization
        self.token = make_admin_token(
            profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        self.profile_client = service.control.Client('profile', token=self.token)
        self.organization_client = service.control.Client('organization', token=self.token)

    def _fixture_path(self, fixture_name):
        return os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            fixture_name,
        )

    def _commit_fixture(self, fixture_name):
        parser = Parser(
            organization_domain=self.organization.domain,
            filename=self._fixture_path(fixture_name),
            token=self.token,
        )
        parser.parse(commit=True)

    def test_parser_no_commit(self):
        parser = Parser(
            organization_domain=self.organization.domain,
            filename=self._fixture_path('sample_organization.csv'),
            token=self.token,
        )
        parser.parse(commit=False)
        response = self.profile_client.call_action('get_profiles')
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    @patch(
        'onboarding.parsers.organizations.get_timezone_for_location',
        return_value='America/Los_Angeles',
    )
    def test_parser_commit(self, mock_get_timezone_for_location):
        parser = Parser(
            organization_domain=self.organization.domain,
            filename=self._fixture_path('sample_organization.csv'),
            token=self.token,
        )
        parser.parse(commit=True)
        response = self.profile_client.call_action('get_profiles')
        self.assertTrue(len(response.result.profiles) > 0)

    @unittest.skip('some transaction block issue')
    def test_parser_idempotent(self):
        self._commit_fixture('sample_organization.csv')
        # commit the fixture again
        self._commit_fixture('sample_organization.csv')
