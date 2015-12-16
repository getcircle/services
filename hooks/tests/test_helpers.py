from services.test import (
    mocks,
    MockedTestCase,
)

from .. import helpers


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()

    def test_get_profile_resource_url(self):
        profile = mocks.mock_profile(organization_id=self.organization.id)
        url = helpers.get_profile_resource_url(self.organization.domain, profile)
        self.assertEqual(url, 'http://%s.local.lunohq.com:3000/profile/%s' % (
            self.organization.domain,
            profile.id,
        ))

    def test_get_post_resource_url(self):
        post = mocks.mock_post(organization_id=self.organization.id)
        url = helpers.get_post_resource_url(self.organization.domain, post)
        self.assertEqual(url, 'http://%s.local.lunohq.com:3000/post/%s' % (
            self.organization.domain,
            post.id,
        ))

    def test_get_post_edit_resource_url(self):
        post = mocks.mock_post(organization_id=self.organization.id)
        url = helpers.get_post_resource_url(self.organization.domain, post, edit=True)
        self.assertEqual(url, 'http://%s.local.lunohq.com:3000/post/%s/edit' % (
            self.organization.domain,
            post.id,
        ))
