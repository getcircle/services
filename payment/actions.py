from django.conf import settings
import stripe

from service import actions


class StoreToken(actions.Action):

    required_fields = ('token', 'email')

    def pre_run(self, *args, **kwargs):
        super(StoreToken, self).pre_run(*args, **kwargs)
        stripe.api_key = settings.STRIPE_API_KEY

    def run(self, *args, **kwargs):
        stripe.Customer.create(
            source=self.request.token,
            email=self.request.email,
        )
