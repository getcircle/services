from __future__ import absolute_import
import uuid

import arrow
from factory.fuzzy import *  # NOQA


class FuzzyUUID(BaseFuzzyAttribute):

    def fuzz(self):
        value = uuid.uuid4()
        return str(value)


class FuzzyTimestamp(BaseFuzzyAttribute):

    def fuzz(self):
        return arrow.utcnow().timestamp
