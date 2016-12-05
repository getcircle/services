from __future__ import absolute_import
from uuid import uuid4

import arrow
from factory.fuzzy import *  # NOQA


class FuzzyUUID(BaseFuzzyAttribute):

    def fuzz(self):
        value = uuid4()
        return str(value)


class FuzzyTimestamp(BaseFuzzyAttribute):

    def fuzz(self):
        return arrow.utcnow().timestamp


uuid = FuzzyUUID().fuzz
text = FuzzyText().fuzz
email = FuzzyText(suffix='@example.com').fuzz
