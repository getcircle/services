import os
import service.control

from services.test import TestCase

from . import parsers


class TestParser(TestCase):

    def setUp(self):
        self.client = service.control.Client(
            'organization',
            token='test-token',
        )

        response = self.client.call_action(
            'create_organization',
            organization={
                'name': 'RH Labs Inc.',
                'domain': 'rhlabs.com',
            },
        )
        self.assertTrue(response.success)
        self.organization = response.result.organization

    def _fixture_path(self, fixture_name):
        return os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            fixture_name,
        )

    def test_parser(self):
        parser = parsers.Parser(
            organization_domain=self.organization.domain,
            filename=self._fixture_path('sample_organization.csv'),
            token='test-token',
        )
        parser.parse(commit=True)
