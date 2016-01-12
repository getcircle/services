from bleach.encoding import force_unicode
import html5lib
from html5lib.constants import tokenTypes
from html5lib.serializer import serialize
from html5lib.tokenizer import HTMLTokenizer


class PostSanitizerMixin(object):

    def sanitize_token(self, token):
        if token.get('name') in ['br']:
            return {'type': tokenTypes['SpaceCharacters'], 'data': '\n'}
        elif token['type'] == tokenTypes['Characters']:
            # Append whitespace to account for tokens being removed. ie.:
            #   <div><span>some text</span><a href="some link">link</a></div>
            #
            #   will translate to:
            #
            #   some textlink
            #
            # if we append whitespace, we'll get something we can display and search against:
            #
            #   some text link
            token['data'] = token['data'] + ' '
            return token


class PostSanitizer(HTMLTokenizer, PostSanitizerMixin):

    def __iter__(self):
        for token in HTMLTokenizer.__iter__(self):
            token = self.sanitize_token(token)
            if token:
                yield token


def transform_html(text):
    text = force_unicode(text)
    parser = html5lib.HTMLParser(tokenizer=PostSanitizer)
    tree = parser.parseFragment(text)
    try:
        serialized = serialize(tree).strip()
    except TypeError:
        serialized = ''
    return force_unicode(serialized)
