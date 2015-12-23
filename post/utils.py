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


bleach.ALLOWED_TAGS.extend([
    'div',
    'br',
    'pre',
    'p',
    'img',
    'figure',
    'figcaption',
])

bleach.ALLOWED_ATTRIBUTES['img'] = _compose(
    white_listed_attributes('src', 'width', 'height'),
    allow_trix_attributes,
)
bleach.ALLOWED_ATTRIBUTES['a'] = _compose(
    white_listed_attributes('href', 'title'),
    allow_trix_attributes,
)
bleach.ALLOWED_ATTRIBUTES['figure'] = ['class']
bleach.ALLOWED_ATTRIBUTES['figcaption'] = ['class']


def clean(value):
    return bleach.clean(value)
