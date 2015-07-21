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
        self.token = mocks.mock_token(
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

    def _mock_get_profile_stats(self, mock):
        service = 'profile'
        action = 'get_profile_stats'
        mock_response = mock.get_mockable_response(service, action)
        for fake_id in range(3):
            stat = mock_response.stats.add()
            stat.id = str(fake_id)
            stat.count = 5

        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            mock_regex_lookup=r'%s:%s:.*' % (service, action,),
        )

    def test_parser_no_commit(self):
        parser = Parser(
            organization_domain=self.organization.domain,
            filename=self._fixture_path('sample_organization.csv'),
            token=self.token,
        )
        parser.parse(commit=False)
        with self.mock_transport(self.profile_client) as mock:
            self._mock_get_profile_stats(mock)

        response = self.organization_client.call_action(
            'get_teams',
            organization_id=self.organization.id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.teams), 0)

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
        with self.mock_transport() as mock:
            mock.instance.register_empty_response(
                service='profile',
                action='get_profile_stats',
                mock_regex_lookup='profile:get_profile_stats.*',
            )
            mock.instance.register_mock_object(
                service='profile',
                action='get_profile',
                return_object_path='profile',
                return_object=self.profile,
                profile_id=self.profile.id,
            )
            response = self.organization_client.call_action(
                'get_teams',
                organization_id=self.organization.id,
            )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.teams), 12)

    @unittest.skip('some transaction block issue')
    def test_parser_idempotent(self):
        self._commit_fixture('sample_organization.csv')
        response = self.organization_client.call_action(
            'get_teams',
            organization_id=self.organization.id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.teams), 12)

        # commit the fixture again
        self._commit_fixture('sample_organization.csv')

        # verify we have the same data
        response = self.organization_client.call_action(
            'get_teams',
            organization_id=self.organization.id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.teams), 12)
