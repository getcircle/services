from rest_framework.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
)
from rest_framework.test import APIRequestFactory

from services.test import (
    mocks,
    TestCase,
    TestAuthView,
)
from .. import factories


class TestUserTokenAuthentication(TestCase):

    def setUp(self):
        self.request_factory = APIRequestFactory()
        self.view = TestAuthView.as_view()

    def test_service_token_authentication_invalid_token(self):
        request = self.request_factory.get('/', HTTP_AUTHORIZATION='Token 12345')
        response = self.view(request)
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_service_token_authentication_token_does_not_exist(self):
        request = self.request_factory.get(
            '/',
            HTTP_AUTHORIZATION='Token %s' % (mocks.mock_token(),),
        )
        response = self.view(request)
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_service_token_authentication_auth_token_empty(self):
        request = self.request_factory.get(
            '/',
            HTTP_AUTHORIZATION='Token %s' % (mocks.mock_token(auth_token=None),),
        )
        response = self.view(request)
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_service_token_authentication_no_auth(self):
        request = self.request_factory.get('/')
        response = self.view(request)
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_service_token_authentication(self):
        token = factories.TokenFactory.create()
        service_token = mocks.mock_token(auth_token=token.key, user_id=token.user_id)
        request = self.request_factory.get('/', HTTP_AUTHORIZATION='Token %s' % (service_token,))
        response = self.view(request)
        self.assertEqual(response.status_code, HTTP_200_OK)
