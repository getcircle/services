from itsdangerous import BadTimeSignature

from protobufs.services.user.containers import token_pb2

from ..test import (
    fuzzy,
    TestCase,
)
from .. import token


class TestServiceTokens(TestCase):

    def test_make_token_and_parse_token(self):
        auth_token = fuzzy.FuzzyUUID().fuzz()
        auth_token_id = fuzzy.FuzzyUUID().fuzz()
        user_id = fuzzy.FuzzyUUID().fuzz()
        profile_id = fuzzy.FuzzyUUID().fuzz()
        organization_id = fuzzy.FuzzyUUID().fuzz()

        expected = token.make_token(
            auth_token=auth_token,
            auth_token_id=auth_token_id,
            user_id=user_id,
            profile_id=profile_id,
            organization_id=organization_id,
            client_type=token_pb2.IOS,
        )
        self.assertTrue(isinstance(expected, basestring))

        parsed = token.parse_token(expected)
        self.assertTrue(isinstance(parsed, token.ServiceToken))

        self.assertEqual(parsed.auth_token, auth_token)
        self.assertEqual(parsed.auth_token_id, auth_token_id)
        self.assertEqual(parsed.profile_id, profile_id)
        self.assertEqual(parsed.organization_id, organization_id)
        self.assertEqual(parsed.user_id, user_id)
        self.assertEqual(parsed.client_type, token_pb2.IOS)

    def test_altering_token_raises_error(self):
        auth_token = fuzzy.FuzzyUUID().fuzz()
        user_id = fuzzy.FuzzyUUID().fuzz()

        expected = token.make_token(
            auth_token=auth_token,
            auth_token_id=fuzzy.FuzzyUUID().fuzz(),
            user_id=user_id,
            client_type=token_pb2.WEB,
        )
        with self.assertRaises(BadTimeSignature):
            token.parse_token(expected[:-11])

    def test_make_admin_token(self):
        expected = token.make_admin_token()
        parsed = token.parse_token(expected)
        self.assertEqual(parsed.auth_token, token.ServiceToken.admin_key)
        self.assertTrue(parsed.is_admin())
        self.assertIsNone(parsed.user_id)
        self.assertIsNone(parsed.organization_id)
