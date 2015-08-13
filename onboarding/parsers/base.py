import service.control

from services.token import (
    make_token,
    parse_token,
)


class OrganizationParser(object):

    def __init__(self, organization_domain, filename, token, verbose=False):
        self.filename = filename
        self.verbose = verbose
        self.organization_client = service.control.Client('organization', token=token)

        self.organization = self._fetch_organization(organization_domain)
        token_data = parse_token(token).as_dict()
        token_data['organization_id'] = self.organization.id
        self.token = make_token(**token_data)
        self.organization_client.token = self.token

    def _fetch_organization(self, organization_domain):
        response = self.organization_client.call_action(
            'get_organization',
            organization_domain=organization_domain,
        )
        return response.result.organization

    def debug_log(self, message):
        if self.verbose:
            print message
