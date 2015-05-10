

class BaseGroupsProvider(object):

    def __init__(self, organization, requester_profile):
        self.organization = organization
        self.requester_profile = requester_profile

    def list_groups_for_profile(self, profile, **kwargs):
        raise NotImplementedError('Subclass must implement `list_groups_for_profile`')

    def list_groups_for_organization(self, **kwargs):
        raise NotImplementedError('Subclass must implement `list_groups_for_organization`')

    def list_members_for_group(self, group_email, role, **kwargs):
        raise NotImplementedError('Subclass must implement `list_members_for_group`')
