import urllib
import urlparse

from django.conf import settings
from itsdangerous import TimestampSigner
from protobufs.user_service_pb2 import UserService
import service.control

from services.test import TestCase


class TestAuthorizationInstructions(TestCase):

    def setUp(self):
        self.client = service.control.Client('user')

    def test_get_authorization_instructions_linkedin(self):
        response = self.client.call_action(
            'get_authorization_instructions',
            identity=UserService.LINKEDIN,
        )
        self.assertTrue(response.success)
        self.assertTrue(response.result.authorization_url)

        url = urlparse.urlparse(response.result.authorization_url)
        params = dict(urlparse.parse_qsl(url.query))
        self.assertEqual(params['response_type'], 'code')
        self.assertEqual(params['redirect_uri'], settings.LINKEDIN_REDIRECT_URI)
        self.assertEqual(urllib.unquote(params['scope']), settings.LINKEDIN_SCOPE)
        self.assertEqual(params['client_id'], settings.LINKEDIN_CLIENT_ID)

        state = params['state']
        signer = TimestampSigner(settings.SECRET_KEY)
        self.assertEqual(signer.unsign(state), str(UserService.LINKEDIN))
