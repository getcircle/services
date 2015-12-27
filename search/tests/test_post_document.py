from services.test import (
    mocks,
    MockedTestCase,
)

from search.stores.es.types.post.document import PostV1
from search.stores.es.types.post.utils import transform_html


class Test(MockedTestCase):

    def test_transform_html(self):
        content = """<div><strong>Some Section<br><br><br></strong>some example code:<br><br></div><pre>def something():\n    print \'this\'\n    print \'other thing\'\n\nsomething()</pre><div><br>some other code section:<br><br></div><pre>def other_thing():\n    print \'this\'\n    print \'else\'\n\nother_thing()</pre><div><br>then close out with<br><br><strong>ending section<br></strong><strong><a data-trix-attachment=\'{"contentType":"image/jpeg","filename":"209.JPG","filesize":419569,"height":1013,"href":"https://dev-lunohq-files.s3.amazonaws.com/6643841e0c724af8b33dda06e40dae43%2F209.JPG","url":"https://dev-lunohq-files.s3.amazonaws.com/6643841e0c724af8b33dda06e40dae43%2F209.JPG","width":1520}\' data-trix-attributes=\'{"caption":"some caption"}\' data-trix-content-type="image/jpeg" href="https://dev-lunohq-files.s3.amazonaws.com/6643841e0c724af8b33dda06e40dae43%2F209.JPG"><figure class="attachment attachment-preview jpg"><img height="1013" src="https://dev-lunohq-files.s3.amazonaws.com/6643841e0c724af8b33dda06e40dae43%2F209.JPG" width="1520"><figcaption class="caption caption-edited">some caption</figcaption></figure></a></strong><strong><br></strong><br></div>"""
        expected = """Some Section \n\n\nsome example code: \n\ndef something():\n    print 'this'\n    print 'other thing'\n\nsomething() \nsome other code section: \n\ndef other_thing():\n    print 'this'\n    print 'else'\n\nother_thing() \nthen close out with \n\nending section \nsome caption"""
        transformed = transform_html(content)
        self.assertEqual(transformed, expected)

    def test_transform_html_unordered_list(self):
        content = '<ul><li>something</li><li>else</li><li>here</li></ul>'
        expected = 'something else here'
        transformed = transform_html(content)
        self.assertEqual(transformed, expected)

    def test_transform_html_ordered_list(self):
        content = '<ol><li>something</li><li>else</li><li>here</li></ol>'
        expected = 'something else here'
        transformed = transform_html(content)
        self.assertEqual(transformed, expected)

    def test_transform_html_trix_image(self):
        content = '<a href="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG" data-trix-attachment="{&quot;contentType&quot;:&quot;image/jpeg&quot;,&quot;filename&quot;:&quot;207.JPG&quot;,&quot;filesize&quot;:298046,&quot;height&quot;:915,&quot;href&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG&quot;,&quot;url&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG&quot;,&quot;width&quot;:1520}" data-trix-content-type="image/jpeg" data-trix-attributes="{&quot;caption&quot;:&quot;some caption here&quot;}"><figure class="attachment attachment-preview jpg"><img src="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG" width="1520" height="915"><figcaption class="caption caption-edited">some caption here</figcaption></figure>'
        expected = 'some caption here'
        transformed = transform_html(content)
        self.assertEqual(transformed, expected)

    def test_from_protobuf(self):
        content = '<div><strong>some title</strong><a href="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG" data-trix-attachment="{&quot;contentType&quot;:&quot;image/jpeg&quot;,&quot;filename&quot;:&quot;207.JPG&quot;,&quot;filesize&quot;:298046,&quot;height&quot;:915,&quot;href&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG&quot;,&quot;url&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG&quot;,&quot;width&quot;:1520}" data-trix-content-type="image/jpeg" data-trix-attributes="{&quot;caption&quot;:&quot;some caption here&quot;}"><figure class="attachment attachment-preview jpg"><img src="https://dev-lunohq-files.s3.amazonaws.com/d01a0c489bde41d9a75acbb0947bb150%2F207.JPG" width="1520" height="915"><figcaption class="caption caption-edited">some caption here</figcaption></figure></a><br><em>if you have more questions, look&nbsp;</em><a href="https://www.google.com"><em>here</em></a></div><pre>code block</pre><ul><li>list<ul><li>here<ul><li>there</li></ul></li></ul></li></ul><ol><li>numbered list<ol><li>here<ol><li>there</li></ol></li></ol></li></ol><div><strong>another inline image:<br><br></strong><strong><a href="https://dev-lunohq-files.s3.amazonaws.com/59ac0d91f4b74113a7cbae0be96bae24%2F210.JPG" data-trix-attachment="{&quot;contentType&quot;:&quot;image/jpeg&quot;,&quot;filename&quot;:&quot;210.JPG&quot;,&quot;filesize&quot;:332625,&quot;height&quot;:1013,&quot;href&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/59ac0d91f4b74113a7cbae0be96bae24%2F210.JPG&quot;,&quot;url&quot;:&quot;https://dev-lunohq-files.s3.amazonaws.com/59ac0d91f4b74113a7cbae0be96bae24%2F210.JPG&quot;,&quot;width&quot;:1520}" data-trix-content-type="image/jpeg" data-trix-attributes="{&quot;caption&quot;:&quot;with another caption&quot;}"><figure class="attachment attachment-preview jpg"><img src="https://dev-lunohq-files.s3.amazonaws.com/59ac0d91f4b74113a7cbae0be96bae24%2F210.JPG" width="1520" height="1013"><figcaption class="caption caption-edited">with another caption</figcaption></figure></a></strong></div>'
        post = mocks.mock_post(content=content)
        expected = u'some title some caption here \nif you have more questions, look \xa0 here code block list here there numbered list here there another inline image: \n\nwith another caption'
        document = PostV1.from_protobuf(post)
        self.assertEqual(document.content, expected)
