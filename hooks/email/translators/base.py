import re

from bleach.encoding import force_unicode
import html5lib
from html5lib.serializer import serialize


def _remove_insignificant_whitespace(html):
    return re.sub('>\s+<', '><', html)


def make_translator(translate_element, translate_attachments, clean):
    def _inner(text, inline_attachments_dict, attachments):
        text = force_unicode(text)
        tree = html5lib.parseFragment(text, treebuilder='lxml')[0]
        for element in tree.iter():
            translate_element(element, inline_attachments_dict)

        translate_attachments(tree, attachments)
        serialized = serialize(
            tree,
            tree='lxml',
            quote_attr_values=True,
            strip_whitespace=True,
        ).strip()
        without_whitespace = _remove_insignificant_whitespace(serialized)
        return clean(without_whitespace)
    return _inner
