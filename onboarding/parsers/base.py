from django.utils.encoding import smart_text


class Row(object):

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        if key in self.data:
            return smart_text(self.data[key])

        return super(Row, self).__getattr__(key)

    def is_empty(self):
        return not any(self.data.values())
