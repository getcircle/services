from services.token import parse_token


class BaseGroupsProvider(object):

    def __init__(self, token, requester_profile=None, paginator=None):
        self.requester_profile = requester_profile
        self.token = token
        self.write_access = True
        self.paginator = paginator

    @property
    def organization_id(self):
        if not hasattr(self, '_token'):
            self._token = parse_token(self.token)
        return self._token.organization_id

    def get_groups_for_profile(self, profile, **kwargs):
        raise NotImplementedError('Subclass must implement `get_groups_for_profile`')

    def get_groups_for_organization(self, **kwargs):
        raise NotImplementedError('Subclass must implement `get_groups_for_organization`')

    def get_groups_with_keys(self, keys, **kwargs):
        raise NotImplementedError('Subclass must implement `get_groups_with_keys`')

    def get_members_for_group(self, group_key, role, **kwargs):
        raise NotImplementedError('Subclass must implement `get_members_for_group`')

    def get_group(self, group_key, **kwargs):
        raise NotImplementedError('Subclass must implement `get_group`')

    def join_group(self, group_key, **kwargs):
        raise NotImplementedError('Subclass must implement `join_group`')

    def leave_group(self, group_key, **kwargs):
        raise NotImplementedError('Subclass must implement `leave_group`')

    def approve_request_to_join(self, request, **kwargs):
        raise NotImplementedError('Subclass must implement `approve_request_to_join`')

    def deny_request_to_join(self, request, **kwargs):
        raise NotImplementedError('Subclass msut implement `deny_request_to_join`')
