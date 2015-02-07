import uuid

from django.conf import settings
from itsdangerous import URLSafeTimedSerializer


class MissingTokenParameter(Exception):

    def __init__(self, field, *args, **kwargs):
        message = 'Missing required token parameter: "%s"' % (field,)
        return super(MissingTokenParameter, self).__init__(message, *args, **kwargs)


class ServiceToken(object):

    required_fields = ('auth_token', 'user_id')
    optional_fields = ('profile_id', 'organization_id')

    def __init__(self, token=None, *args, **kwargs):
        self._token = token
        for field in self.required_fields:
            try:
                setattr(self, field, kwargs[field])
            except KeyError:
                raise MissingTokenParameter(field)

        for field in self.optional_fields:
            setattr(self, field, kwargs.get(field))

    def as_dict(self):
        output = {}
        for field in (self.required_fields + self.optional_fields):
            value = getattr(self, field, None)
            if isinstance(value, uuid.UUID):
                value = str(value)
            output[field] = value
        return output


def make_token(**values):
    token = ServiceToken(**values)
    serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
    return serializer.dumps(token.as_dict())


def parse_token(token):
    serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
    token_values = serializer.loads(token)
    return ServiceToken(token=token, **token_values)
