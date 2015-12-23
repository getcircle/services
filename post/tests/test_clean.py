from services.test import MockedTestCase

from ..utils import clean


class Test(MockedTestCase):

    def test_clean_trix_a_tag(self):
        content = '<a href="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG" data-trix-attachment="{&quot;contentType&quot;:&quot;image/jpeg&quot;,&quot;filename&quot;:&quot;207.JPG&quot;,&quot;filesize&quot;:298046,&quot;height&quot;:915,&quot;href&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG&quot;,&quot;url&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG&quot;,&quot;width&quot;:1520}" data-trix-content-type="image/jpeg" data-trix-attributes="{&quot;caption&quot;:&quot;some caption here&quot;}">'
        cleaned = clean(content)
        self.assertIn('<a', cleaned)
        self.assertIn(
            'href="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG"',
            cleaned,
        )
        self.assertIn('data-trix-attachment=', cleaned)
        self.assertIn('data-trix-content-type=', cleaned)
        self.assertIn('data-trix-attributes=', cleaned)

    def test_clean_figure(self):
        content = '<figure class="attachment attachment-preview jpg"></figure>'
        cleaned = clean(content)
        self.assertEqual(content, cleaned)

    def test_clean_img(self):
        content = '<img src="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG" width="1520" height="915">'
        cleaned = clean(content)
        self.assertIn('src=', cleaned)
        self.assertIn('width="1520"', cleaned)
        self.assertIn('height="915"', cleaned)

    def test_clean_figcaption(self):
        content = '<figcaption class="caption caption-edited">some caption here</figcaption>'
        cleaned = clean(content)
        self.assertEqual(content, cleaned)

    def test_clean_div(self):
        content = '<div>something</div>'
        cleaned = clean(content)
        self.assertEqual(content, cleaned)

    def test_clean_pre(self):
        content = '<pre>something</pre>'
        cleaned = clean(content)
        self.assertEqual(content, cleaned)

    def test_clean_lists(self):
        content = '<ul><li>list<ul><li>here<ul><li>there</li></ul></li></ul></li></ul><ol><li>numbered list<ol><li>here<ol><li>there</li></ol></li></ol></li></ol>'
        cleaned = clean(content)
        self.assertEqual(content, cleaned)
