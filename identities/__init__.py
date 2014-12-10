IDENTITY_TYPE_INTERNAL = 0
IDENTITY_TYPE_INTERNAL_NAME = 'INTERNAL'

IDENTITY_TYPES = (
    (IDENTITY_TYPE_INTERNAL, IDENTITY_TYPE_INTERNAL_NAME),
)

IDENTITY_TYPE_TO_NAME_MAP = dict(IDENTITY_TYPES)
IDENTITY_NAME_TO_TYPE_MAP = zip(
    IDENTITY_TYPE_TO_NAME_MAP.values(),
    IDENTITY_TYPE_TO_NAME_MAP.keys(),
)
