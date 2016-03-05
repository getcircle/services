import re

import service.control
from django.conf import settings

from services.test import (
    mocks,
    MockedTestCase,
)

from .. import factories


class TestFiles(MockedTestCase):

    def setUp(self):
        super(TestFiles, self).setUp()
        self.organization = mocks.mock_organization(domain='acme')
        self.profile = mocks.mock_profile()
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=self.profile.id,
        )

    def test_no_token_or_organization_no_source_url(self):
        file = factories.FileFactory.create()
        file_protobuf = file.to_protobuf()
        self.assertEqual(file_protobuf.source_url, '')

    def test_source_url_without_domain(self):
        file = factories.FileFactory.create()
        file_protobuf = file.to_protobuf(token=self.token)
        expected_source_url = '%s/file/%s/%s' % (settings.FRONTEND_URL, file.id, file.name,)
        self.assertEqual(file_protobuf.source_url, expected_source_url)

    def test_source_url_with_domain_using_token(self):
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object=self.organization,
            return_object_path='organization',
        )

        scheme = 'https'
        frontend_url = settings.FRONTEND_URL
        scheme_match = re.match(r'^(\w+):\/\/\S+$', frontend_url)
        if scheme_match:
            scheme = scheme_match.group(1)
            frontend_url = frontend_url[len(scheme + '://'):]

        file = factories.FileFactory.create()
        file_protobuf = file.to_protobuf(token=self.token)
        expected_source_url = '%s://%s.%s/file/%s/%s' % (scheme, self.organization.domain, frontend_url, file.id, file.name,)
        self.assertEqual(file_protobuf.source_url, expected_source_url)

    def test_source_url_with_domain_using_fetched_organization(self):
        scheme = 'https'
        frontend_url = settings.FRONTEND_URL
        scheme_match = re.match(r'^(\w+):\/\/\S+$', frontend_url)
        if scheme_match:
            scheme = scheme_match.group(1)
            frontend_url = frontend_url[len(scheme + '://'):]

        file = factories.FileFactory.create()
        file_protobuf = file.to_protobuf(organization=self.organization)
        expected_source_url = '%s://%s.%s/file/%s/%s' % (scheme, self.organization.domain, frontend_url, file.id, file.name,)
        self.assertEqual(file_protobuf.source_url, expected_source_url)
