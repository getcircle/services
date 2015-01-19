from __future__ import absolute_import
import uuid
from factory.fuzzy import *  # NOQA


class FuzzyUUID(BaseFuzzyAttribute):

    def fuzz(self):
        return uuid.uuid4().hex
