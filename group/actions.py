from service import actions
import service.control
from services.token import parse_token

from . import providers


class ListGroups(actions.Action):

    required_fields = ('provider',)

    def pre_run(self, *args, **kwargs):
        self.parsed_token = parse_token(self.token)
        self.parsed_token.organization_id
        self.organization = service.control.get_object(
            'organization',
            client_kwargs={'token': self.token},
            action='get_organization',
            action_kwargs={'organization_id': self.parsed_token.organization_id},
            return_object='organization',
        )
        self.profile = service.control.get_object(
            'profile',
            client_kwargs={'token': self.token},
            action='get_profile',
            action_kwargs={'profile_id': self.parsed_token.profile_id},
            return_object='profile',
        )

    def run(self, *args, **kwargs):
        provider = providers.Google(self.organization, self.profile)
        if self.request.HasField('profile_id'):
            for_profile = service.control.get_object(
                'profile',
                client_kwargs={'token': self.token},
                action='get_profile',
                action_kwargs={'profile_id': self.parsed_token.profile_id},
                return_object='profile',
            )
            groups = provider.list_groups_for_profile(for_profile)
        else:
            groups = provider.list_groups_for_organization()

        self.response.groups.extend(groups)


class JoinGroup(actions.Action):

    def run(self, *args, **kwargs):
        pass


class RespondToMembershipRequest(actions.Action):

    def run(self, *args, **kwargs):
        pass


class LeaveGroup(actions.Action):

    def run(self, *args, **kwargs):
        pass


class ListMembers(actions.Action):

    def run(self, *args, **kwargs):
        pass


class GetGroup(actions.Action):

    def run(self, *args, **kwargs):
        pass
