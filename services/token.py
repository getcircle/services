import uuid

from django.conf import settings
from itsdangerous import URLSafeTimedSerializer


class MissingTokenParameter(Exception):

    def __init__(self, field, message=None, *args, **kwargs):
        if message is None:
            message = 'Missing required token parameter: "%s"' % (field,)
        return super(MissingTokenParameter, self).__init__(message, *args, **kwargs)


class ServiceToken(object):

    admin_key = 'ADMIN'
    required_fields = ('auth_token',)
    optional_fields = ('profile_id',)
    one_of_fields = ('organization_id', 'user_id')

    def __init__(self, token=None, *args, **kwargs):
        self._token = token

        for field in self.required_fields:
            try:
                setattr(self, field, kwargs[field])
            except KeyError:
                raise MissingTokenParameter(field)

        one_of = False
        for field in self.one_of_fields:
            if field in kwargs:
                setattr(self, field, kwargs[field])
                one_of = True

        if not one_of and not self.is_admin():
            raise MissingTokenParameter(
                None,
                message='Must provide either "user_id" or "organization_id"',
            )

        for field in self.optional_fields:
            setattr(self, field, kwargs.get(field))

    def as_dict(self):
        output = {}
        for field in (self.required_fields + self.optional_fields + self.one_of_fields):
            value = getattr(self, field, None)
            if isinstance(value, uuid.UUID):
                value = str(value)
            output[field] = value
        return output

    def is_admin(self):
        return self.auth_token == self.admin_key


def make_token(**values):
    token = ServiceToken(**values)
    serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
    return serializer.dumps(token.as_dict())


def parse_token(token):
    serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
    token_values = serializer.loads(token)
    return ServiceToken(token=token, **token_values)


# XXX think through all the cases where this could be vulnerable
def make_admin_token(**values):
    values['auth_token'] = ServiceToken.admin_key
    return make_token(**values)
