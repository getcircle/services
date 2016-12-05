import json
from rest_framework.test import (
    APIClient as RestFrameworkAPIClient,
    APITestCase as RestFrameworkAPITestCase,
)


class APIClient(RestFrameworkAPIClient):

    def post(self, *args, **kwargs):
        response = super(APIClient, self).post(*args, **kwargs)
        try:
            response.json = json.loads(response.content)
        except ValueError:
            response.json = None
        return response


class APITestCase(RestFrameworkAPITestCase):
    client_class = APIClient
