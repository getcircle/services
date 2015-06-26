from mock import patch
import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)


class TestSearch(TestCase):

    def setUp(self):
        super(TestSearch, self).setUp()
