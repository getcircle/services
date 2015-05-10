

class BaseGroupsProvider(object):

    def __init__(self, organization, requester_profile):
        self.organization = organization
        self.requester_profile = requester_profile

    def list_for_profile(self, profile, **kwargs):
        raise NotImplementedError('Subclass must implement `list_for_profile`')

    def list_for_organization(self, **kwargs):
        raise NotImplementedError('Subclass must implement `list_for_organization`')
