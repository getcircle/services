import arrow
from oauth2client.client import AccessTokenInfo
from services.test import fuzzy


class MockCredentials(object):

    def __init__(self, id_token):
        self.id_token = id_token
        self.token_expiry = arrow.utcnow()
        self.access_token = fuzzy.FuzzyUUID().fuzz()
        self.refresh_token = fuzzy.FuzzyUUID().fuzz()

    def get_access_token(self):
        return AccessTokenInfo(access_token=self.access_token, expires_in=self.token_expiry)
