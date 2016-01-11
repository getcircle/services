from mock import patch
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


class TestDeletePosts(MockedTestCase):

    def setUp(self):
        super(TestDeletePosts, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

    def test_delete_post_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action('delete_post')

    def test_delete_post_invalid_id(self):
        with self.assertFieldError('id'):
            self.client.call_action('delete_post', id='invalid')

    def test_delete_post_not_author_rejected(self):
        post = factories.PostFactory.create_protobuf(organization_id=self.organization.id)
        with self.assertRaisesCallActionError() as expected:
            self.client.call_action('delete_post', id=post.id)
        self.assertIn('PERMISSION_DENIED', expected.exception.response.errors)

    def test_delete_post_does_not_exist(self):
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_post', id=fuzzy.FuzzyUUID().fuzz())

    def test_delete_post_wrong_organization(self):
        post = factories.PostFactory.create_protobuf()
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_post', id=post.id)

    def test_delete_post(self):
        post = factories.PostFactory.create_protobuf(profile=self.profile)
        self.client.call_action('delete_post', id=post.id)
        self.assertFalse(models.Post.objects.filter(pk=post.id).exists())

    @patch('post.editors.trix.service.control.call_action')
    def test_delete_post_with_inline_attachments(self, patched):
        content = '<div>something else with attachments<br><br><a data-trix-attachment=\'{"contentType":"image/jpeg","fileId":"d057cbd4-eb1e-4129-9ecb-3ca6b87002c9","filename":"207.JPG","href":"https://dev-lunohq-files.s3.amazonaws.com/32adb03b40fa471d9b4a037c4f01bc46%2F207.JPG","url":"https://dev-lunohq-files.s3.amazonaws.com/32adb03b40fa471d9b4a037c4f01bc46%2F207.JPG"}\' data-trix-content-type="image/jpeg" href="https://dev-lunohq-files.s3.amazonaws.com/32adb03b40fa471d9b4a037c4f01bc46%2F207.JPG"><figure class="attachment attachment-preview jpeg"><img src="https://dev-lunohq-files.s3.amazonaws.com/32adb03b40fa471d9b4a037c4f01bc46%2F207.JPG"><figcaption class="caption">207.JPG <span>291.06 KB</span></figcaption></figure></a><a data-trix-attachment=\'{"contentType":"image/jpeg","fileId":"63d3318f-2e6b-4872-9840-de01d1efb41b","filename":"208.JPG","href":"https://dev-lunohq-files.s3.amazonaws.com/652ca31de57f4eb5b3029751b951c17c%2F208.JPG","url":"https://dev-lunohq-files.s3.amazonaws.com/652ca31de57f4eb5b3029751b951c17c%2F208.JPG"}\' data-trix-content-type="image/jpeg" href="https://dev-lunohq-files.s3.amazonaws.com/652ca31de57f4eb5b3029751b951c17c%2F208.JPG"><figure class="attachment attachment-preview jpeg"><img src="https://dev-lunohq-files.s3.amazonaws.com/652ca31de57f4eb5b3029751b951c17c%2F208.JPG"><figcaption class="caption">208.JPG <span>400.91 KB</span></figcaption></figure></a></div>'
        post = factories.PostFactory.create_protobuf(profile=self.profile, content=content)
        self.client.call_action('delete_post', id=post.id)
        self.assertFalse(models.Post.objects.filter(pk=post.id).exists())

        call_args = [call_args[1] for call_args in patched.call_args_list
                     if call_args[1]['service'] == 'file' and call_args[1]['action'] == 'delete']
        self.assertTrue(call_args)
        call_args = call_args[0]
        self.assertEqual(len(call_args['ids']), 2)
        self.assertEqual(
            call_args['ids'],
            ['d057cbd4-eb1e-4129-9ecb-3ca6b87002c9', '63d3318f-2e6b-4872-9840-de01d1efb41b'],
        )
