import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from ..models import Attachment
from ..utils import clean


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        token = mocks.mock_token(organization_id=self.organization.id, profile_id=self.profile.id)
        self.client = service.control.Client('post', token=token)
        self.mock.instance.dont_mock_service('post')

    def test_create_post_post_required(self):
        with self.assertFieldError('post', 'MISSING'):
            self.client.call_action('create_post')

    def test_create_post(self):
        post_title = 'some title'
        post_content = 'some text'
        response = self.client.call_action('create_post', post={
            'title': post_title,
            'content': post_content,
        })
        post = response.result.post
        self.assertEqual(post_title, post.title)
        self.assertEqual(post_content, post.content)
        self.assertEqual(self.profile.id, post.by_profile_id)
        self.assertEqual(self.organization.id, post.organization_id)

    def test_create_post_return_by_profile(self):
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profile',
            return_object_path='profile',
            return_object=self.profile,
            profile_id=self.profile.id,
            inflations={'disabled': False, 'only': ['display_title']},
        )
        response = self.client.call_action(
            'create_post',
            post={'title': fuzzy.text(), 'content': fuzzy.text()},
        )
        post = response.result.post
        self.verify_containers(self.profile, post.by_profile)

    def test_create_post_specified_by_profile_id_rejected(self):
        post = {'title': 'title', 'content': 'content', 'by_profile_id': fuzzy.FuzzyUUID().fuzz()}
        response = self.client.call_action('create_post', post=post)
        self.assertEqual(response.result.post.by_profile_id, self.profile.id)

    def test_create_post_specified_organization_id_rejected(self):
        post = {'title': 'title', 'content': 'content', 'organization_id': fuzzy.FuzzyUUID().fuzz()}
        response = self.client.call_action('create_post', post=post)
        self.assertEqual(response.result.post.organization_id, self.organization.id)

    def test_create_post_title_required(self):
        with self.assertFieldError('post.title', 'MISSING'):
            self.client.call_action('create_post', post={'content': 'some content'})

    def test_create_post_content_required(self):
        with self.assertFieldError('post.content', 'MISSING'):
            self.client.call_action('create_post', post={'title': 'title'})

    def test_create_post_with_file_ids(self):
        files = [mocks.mock_file(organization_id=self.organization.id) for _ in range(2)]
        post = {
            'title': 'some title',
            'content': 'some content',
            'file_ids': [f.id for f in files],
        }

        response = self.client.call_action('create_post', post=post)
        self.assertEqual(len(response.result.post.file_ids), len(files))
        attachments = Attachment.objects.filter(post_id=response.result.post.id)
        self.assertEqual(len(attachments), len(files))

    def test_create_post_strip_dangerous_html(self):
        content = """
            <div>
                <strong>Some Title</strong>
                <em>some tldr</em>
                <p>some text</p>
                <script type="text/javascript">evil()</script>
                <iframe src="https://dangerous.com" />
                <img src="https://kittens.com">
            </div>
        """
        response = self.client.call_action(
            'create_post',
            post={'title': 'Some Post', 'content': content},
        )
        post = response.result.post
        self.assertNotIn('<script', post.content)
        self.assertIn('&lt;script type="text/javascript"&gt;evil()&lt;/script&gt;', post.content)
        self.assertIn('<strong>Some Title</strong>', post.content)
        self.assertIn('<p>some text</p>', post.content)
        self.assertIn('<img src="https://kittens.com">', post.content)
        self.assertNotIn('<iframe', post.content)

    def test_create_post_snippet_doesnt_include_html(self):
        content = """
            <div>
                <strong>Some Title</strong>
                <a href="https://lunohq.com">luno</a>
                <span>something here</span>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                Phasellus quis aliquam ipsum, egestas vulputate libero. In
                rutrum tristique ligula, at tristique lorem euismod sed.
                Vivamus quis posuere metus.</p>
            </div>
        """
        response = self.client.call_action(
            'create_post',
            post={'title': 'Some Post', 'content': content},
        )
        post = response.result.post
        self.assertNotIn('<', post.snippet)

    def test_create_post_with_html(self):
        content = '<div><strong>some title</strong><a href="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG" data-trix-attachment="{&quot;contentType&quot;:&quot;image/jpeg&quot;,&quot;filename&quot;:&quot;207.JPG&quot;,&quot;filesize&quot;:298046,&quot;height&quot;:915,&quot;href&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG&quot;,&quot;url&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG&quot;,&quot;width&quot;:1520}" data-trix-content-type="image/jpeg" data-trix-attributes="{&quot;caption&quot;:&quot;some caption here&quot;}"><figure class="attachment attachment-preview jpg"><img src="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG" width="1520" height="915"><figcaption class="caption caption-edited">some caption here</figcaption></figure></a><br><em>if you have more questions, look&nbsp;</em><a href="https://www.google.com"><em>here</em></a></div><pre>code block</pre><ul><li>list<ul><li>here<ul><li>there</li></ul></li></ul></li></ul><ol><li>numbered list<ol><li>here<ol><li>there</li></ol></li></ol></li></ol><div><strong>another inline image:<br><br></strong><strong><a href="https://dev-lunohq-files.s3.amazonaws.com/59ac0d91f4b74113a7cbae0be96bae24%2F210.JPG" data-trix-attachment="{&quot;contentType&quot;:&quot;image/jpeg&quot;,&quot;filename&quot;:&quot;210.JPG&quot;,&quot;filesize&quot;:332625,&quot;height&quot;:1013,&quot;href&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/59ac0d91f4b74113a7cbae0be96bae24%2F210.JPG&quot;,&quot;url&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/59ac0d91f4b74113a7cbae0be96bae24%2F210.JPG&quot;,&quot;width&quot;:1520}" data-trix-content-type="image/jpeg" data-trix-attributes="{&quot;caption&quot;:&quot;with another caption&quot;}"><figure class="attachment attachment-preview jpg"><img src="https://dev-lunohq-files.s3.amazonaws.com/59ac0d91f4b74113a7cbae0be96bae24%2F210.JPG" width="1520" height="1013"><figcaption class="caption caption-edited">with another caption</figcaption></figure></a></strong></div>'
        response = self.client.call_action(
            'create_post',
            post={'title': 'Some Post', 'content': content},
        )
        post = response.result.post
        self.assertEqual(post.content, clean(content))
