from __future__ import absolute_import
import uuid

import arrow
from factory.fuzzy import *  # NOQA


class FuzzyUUID(BaseFuzzyAttribute):

    def __init__(self, as_hex=True, *args, **kwargs):
        self.as_hex = as_hex
        super(FuzzyUUID, self).__init__(*args, **kwargs)

    def fuzz(self):
        value = uuid.uuid4()
        if self.as_hex:
            value = value.hex
        return value


class FuzzyTimestamp(BaseFuzzyAttribute):

    def fuzz(self):
        return arrow.utcnow().timestamp
