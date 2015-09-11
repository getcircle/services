from mock import patch
import service.control

from services.test import (
    fuzzy,
    TestCase,
)


class TestPaymentService(TestCase):

    def setUp(self):
        super(TestPaymentService, self).setUp()
        self.client = service.control.Client('payment')

    def test_store_token_token_required(self):
        with self.assertFieldError('token', 'MISSING'):
            self.client.call_action(
                'store_token',
                email=fuzzy.FuzzyText(suffix='@example.com').fuzz(),
            )

    def test_store_token_email_required(self):
        with self.assertFieldError('email', 'MISSING'):
            self.client.call_action('store_token', token=fuzzy.FuzzyText().fuzz())

    @patch('payment.actions.stripe.Customer')
    def test_store_token_creates_stripe_customer(self, patched):
        token = fuzzy.FuzzyText().fuzz()
        email = fuzzy.FuzzyText(suffix='@example.com').fuzz()
        self.client.call_action('store_token', token=token, email=email)
        call_args = patched.create.call_args_list[0][1]
        self.assertEqual(call_args['source'], token)
        self.assertEqual(call_args['email'], email)
