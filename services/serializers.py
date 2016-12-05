import json
import uuid

from django.core.signing import JSONSerializer as DjangoJSONSerializer

from django.core.serializers.json import (
    DjangoJSONEncoder,
)


class JSONSerializer(DjangoJSONSerializer):

    def dumps(self, value, **kwargs):
        if 'separators' not in kwargs:
            kwargs['separators'] = (',', ':')
        return json.dumps(value, cls=BetterJSONEncoder, **kwargs).encode(
            'latin-1'
        )


class BetterJSONEncoder(DjangoJSONEncoder):

    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super(BetterJSONEncoder, self).default(obj)
