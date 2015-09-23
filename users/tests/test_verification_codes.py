import mock
import service.control
from twilio.rest.exceptions import TwilioRestException

from services.test import (
    fuzzy,
    TestCase,
)
from .. import (
    actions,
    factories,
    models,
)


class TestUsersVerificationCodes(TestCase):

    def setUp(self):
        super(TestUsersVerificationCodes, self).setUp()
        self.client = service.control.Client('user', token='test-token')

    def _mock_twilio(self, mock_class):
        mock_message = mock.MagicMock()
        type(mock_message).sid = mock.PropertyMock(return_value=fuzzy.FuzzyUUID().fuzz())
        mock_class().messages.create.return_value = mock_message

    def test_send_verification_code_invalid_user_id(self):
        with self.assertFieldError('user_id'):
            self.client.call_action('send_verification_code', user_id='invalid')

    def test_send_verification_code_user_does_not_exist(self):
        with self.assertFieldError('user_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'send_verification_code',
                user_id=fuzzy.FuzzyUUID().fuzz(),
            )

    def test_send_verification_code_no_cell_number(self):
        user = factories.UserFactory.create(phone_number=None)
        with self.assertRaises(service.control.CallActionError) as expected:
            self.client.call_action('send_verification_code', user_id=str(user.id))
        self.assertIn('NO_PHONE_NUMBER', expected.exception.response.errors)

    @mock.patch('users.actions.TwilioRestClient')
    def test_send_verification_code_invalid_number(self, mock_class):
        mock_class().messages.create.side_effect = TwilioRestException(
            21542,
            'http://www.twilio.errors/',
            'failed',
        )
        user = factories.UserFactory.create()
        with self.assertRaises(service.control.CallActionError) as expected:
            self.client.call_action('send_verification_code', user_id=str(user.id))
        self.assertIn('FAILED', expected.exception.response.errors)

    @mock.patch('users.actions.TwilioRestClient')
    def test_send_verification_code(self, mock_class):
        self._mock_twilio(mock_class)

        user = factories.UserFactory.create()
        response = self.client.call_action('send_verification_code', user_id=str(user.id))
        self.assertTrue(response.success)
        self.assertTrue(response.result.message_id)

        # verify we created a totp_token for the user
        totp_token = models.TOTPToken.objects.get(user_id=str(user.id))
        self.assertTrue(totp_token.token)

    @mock.patch('users.actions.TwilioRestClient')
    def test_send_verification_code_duplicate(self, mock_class):
        self._mock_twilio(mock_class)

        user = factories.UserFactory.create()
        # create a totp token
        response = self.client.call_action('send_verification_code', user_id=str(user.id))
        self.assertTrue(response.success)

        # ensure we can always create another one
        response = self.client.call_action('send_verification_code', user_id=str(user.id))
        self.assertTrue(response.success)

        # verify we only have 1 token for the user
        self.assertEqual(len(models.TOTPToken.objects.filter(user_id=user.id)), 1)

    def test_verify_verification_code_user_does_not_exist(self):
        with self.assertFieldError('user_id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'verify_verification_code',
                user_id=fuzzy.FuzzyUUID().fuzz(),
                code='invalid',
            )

    def test_verify_verification_code_invalid_user_id(self):
        with self.assertFieldError('user_id'):
            self.client.call_action(
                'verify_verification_code',
                user_id='invalid',
                code='invalid',
            )

    def test_verify_verification_code_invalid_code(self):
        token = factories.TOTPTokenFactory.create()
        with self.assertFieldError('code'):
            self.client.call_action(
                'verify_verification_code',
                user_id=str(token.user_id),
                code='789878',
            )

        user = models.User.objects.get(pk=token.user_id)
        self.assertFalse(user.phone_number_verified)

    def test_verify_verification_code(self):
        user = factories.UserFactory.create()
        code = models.TOTPToken.objects.totp_for_user(user)
        response = self.client.call_action(
            'verify_verification_code',
            user_id=str(user.id),
            code=code,
        )
        self.assertTrue(response.success)
        self.assertTrue(response.result.verified)

        user = models.User.objects.get(pk=user.id)
        self.assertTrue(user.phone_number_verified)
