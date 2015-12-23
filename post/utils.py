import bleach


def _compose(*functions):
    def _inner(attribute, value):
        return any([func(attribute, value) for func in functions])
    return _inner


def allow_trix_attributes(attribute, value):
    return attribute.startswith('data-trix')


def white_listed_attributes(*white_list):
    def _inner(attribute, value):
        return attribute in white_list
    return _inner


ALLOWED_TAGS = tuple(bleach.ALLOWED_TAGS + [
    'div',
    'br',
    'pre',
    'p',
    'img',
    'figure',
    'figcaption',
])

ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES)
ALLOWED_ATTRIBUTES['img'] = _compose(
    white_listed_attributes('src', 'width', 'height'),
    allow_trix_attributes,
)
ALLOWED_ATTRIBUTES['a'] = _compose(
    white_listed_attributes('href', 'title'),
    allow_trix_attributes,
)
ALLOWED_ATTRIBUTES['figure'] = ['class']
ALLOWED_ATTRIBUTES['figcaption'] = ['class']


def clean(value):
    return bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
