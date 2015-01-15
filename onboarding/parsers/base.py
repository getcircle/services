import service.control


class OrganizationParser(object):

    def __init__(self, organization_domain, filename, token, verbose=False):
        self.filename = filename
        self.token = token
        self.verbose = verbose
        self.organization_client = service.control.Client('organization', token=token)
        self.organization = self._fetch_organization(organization_domain)

    def _fetch_organization(self, organization_domain):
        response = self.organization_client.call_action(
            'get_organization',
            organization_domain=organization_domain,
        )
        return response.result.organization

    def debug_log(self, message):
        if self.verbose:
            print message
