from itsdangerous import BadTimeSignature
from ..test import (
    fuzzy,
    TestCase,
)

from .. import token


class TestServiceTokens(TestCase):

    def test_make_token_and_parse_token(self):
        auth_token = fuzzy.FuzzyUUID().fuzz()
        user_id = fuzzy.FuzzyUUID().fuzz()
        profile_id = fuzzy.FuzzyUUID().fuzz()
        organization_id = fuzzy.FuzzyUUID().fuzz()

        expected = token.make_token(
            auth_token=auth_token,
            user_id=user_id,
            profile_id=profile_id,
            organization_id=organization_id,
        )
        self.assertTrue(isinstance(expected, basestring))

        parsed = token.parse_token(expected)
        self.assertTrue(isinstance(parsed, token.ServiceToken))

        self.assertEqual(parsed.auth_token, auth_token)
        self.assertEqual(parsed.profile_id, profile_id)
        self.assertEqual(parsed.organization_id, organization_id)
        self.assertEqual(parsed.user_id, user_id)

    def test_altering_token_raises_error(self):
        auth_token = fuzzy.FuzzyUUID().fuzz()
        user_id = fuzzy.FuzzyUUID().fuzz()

        expected = token.make_token(auth_token=auth_token, user_id=user_id)
        with self.assertRaises(BadTimeSignature):
            token.parse_token(expected[:-11])
