from __future__ import absolute_import
import uuid

import arrow
from factory.fuzzy import *  # NOQA


class FuzzyUUID(BaseFuzzyAttribute):

    def fuzz(self):
        return uuid.uuid4().hex


class FuzzyTimestamp(BaseFuzzyAttribute):

    def fuzz(self):
        return arrow.utcnow().timestamp
