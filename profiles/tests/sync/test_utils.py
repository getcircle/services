from services.test import (
    fuzzy,
    MockedTestCase,
)

from profiles.sync import utils


class Test(MockedTestCase):

    def test_get_path_from_dict(self):
        source = {
            'id': fuzzy.uuid(),
            'profile': {
                'name': fuzzy.text(),
                'nested': {
                    'nested': {
                        'value': fuzzy.text(),
                    },
                },
            },
        }
        value = utils.get_path_from_dict('id', source)
        self.assertEqual(value, source['id'])
        value = utils.get_path_from_dict('profile.name', source)
        self.assertEqual(value, source['profile']['name'])
        value = utils.get_path_from_dict('profile.nested.nested.value', source)
        self.assertEqual(value, source['profile']['nested']['nested']['value'])

    def test_set_path_in_dict(self):
        source = {
            'id': fuzzy.uuid(),
            'profile': {
                'name': fuzzy.text(),
                'nested': {
                    'other': 'value',
                    'nested': {
                        'value': fuzzy.text(),
                    },
                },
            },
        }
        utils.set_path_in_dict('profile.nested.nested.value', 1, source)
        value = utils.get_path_from_dict('profile.nested.nested.value', source)
        self.assertEqual(value, 1)
        self.assertEqual(
            source['profile']['nested']['other'],
            'value',
            'it shouldn\'t overwrite other values',
        )
