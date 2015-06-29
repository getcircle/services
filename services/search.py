from base64 import b64encode

import watson


class SearchAdapter(watson.SearchAdapter):

    def get_protobuf(self, obj):
        return obj.to_protobuf()

    def get_meta(self, obj):
        container = self.get_protobuf(obj)
        return {
            'protobuf': '.'.join([container.__module__, container.__class__.__name__]),
            'data': b64encode(container.SerializeToString()),
        }
