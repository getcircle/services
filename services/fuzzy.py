import uuid
from factory.fuzzy import *


class FuzzyUUID(BaseFuzzyAttribute):

    def fuzz(self):
        return uuid.uuid4().hex
