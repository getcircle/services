from html5lib import serialize
from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from hooks.email.translators.trix import (
    format_size,
    generate_trix_inline_attachment,
    is_previewable,
)


class Test(MockedTestCase):

    def _serialize(self, tree):
        return serialize(tree, tree='lxml', quote_attr_values=True)

    def test_translate_inline_image_to_trix(self):
        name = fuzzy.text()
        content_type = 'image/png'
        size = 6799
        url = fuzzy.FuzzyText(prefix='https://', suffix='.com').fuzz()
        expected = '<a data-trix-content-type="%(content_type)s" data-trix-attachment=\'{"contentType":"%(content_type)s","filename":"%(name)s","href":"%(url)s","url":"%(url)s"}\' href="%(url)s"><figure class="attachment attachment-preview %(content_sub_type)s"><img src="%(url)s"><figcaption class="caption">%(name)s <span>6.64 KB</span></figcaption></figure></a>' % {
            'name': name,
            'url': url,
            'content_type': content_type,
            'content_sub_type': 'png',
        }
        _file = mocks.mock_file(name=name, content_type=content_type, size=size, source_url=url)
        result = generate_trix_inline_attachment(_file)
        serialized = self._serialize(result)
        self.assertEqual(expected, serialized)

    def test_translate_inline_attachment_to_trix(self):
        name = fuzzy.text()
        content_type = 'video/mp4'
        size = 858092
        url = fuzzy.FuzzyText(prefix='https://', suffix='.com').fuzz()
        expected = '<a data-trix-content-type="%(content_type)s" data-trix-attachment=\'{"contentType":"%(content_type)s","filename":"%(name)s","href":"%(url)s","url":"%(url)s"}\' href="%(url)s"><figure class="attachment attachment-file %(content_sub_type)s"><figcaption class="caption">%(name)s <span>837.98 KB</span></figcaption></figure></a>' % {
            'name': name,
            'url': url,
            'content_type': content_type,
            'content_sub_type': 'mp4',
        }
        _file = mocks.mock_file(name=name, content_type=content_type, size=size, source_url=url)
        result = generate_trix_inline_attachment(_file)
        serialized = self._serialize(result)
        self.assertEqual(expected, serialized)

    def test_format_size(self):
        self.assertEqual(format_size(0), '0 Bytes')
        self.assertEqual(format_size(1), '1 Byte')
        self.assertEqual(format_size(489), '489 Bytes')
        self.assertEqual(format_size(858092), '837.98 KB')
        self.assertEqual(format_size(43230000000), '40.26 GB')

    def test_is_previewable(self):
        self.assertTrue(is_previewable('image/gif'))
        self.assertTrue(is_previewable('image/png'))
        self.assertTrue(is_previewable('image/jpg'))
        self.assertTrue(is_previewable('image/jpeg'))
        self.assertFalse(is_previewable('video/mp4'))
        self.assertFalse(is_previewable('text/html'))
