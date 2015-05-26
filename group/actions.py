from protobufs.services.group.actions import respond_to_membership_request_pb2
from service import (
    actions,
    validators,
)
import service.control
from services.token import parse_token

from . import (
    models,
    providers,
)


def is_valid_membership_request(value):
    return models.GroupMembershipRequest.objects.filter(id=value).exists()


class PreRunParseTokenMixin(object):

    def pre_run(self, *args, **kwargs):
        self.parsed_token = parse_token(self.token)
        self.organization = service.control.get_object(
            'organization',
            client_kwargs={'token': self.token},
            action='get_organization',
            return_object='organization',
            organization_id=self.parsed_token.organization_id,
        )
        self.profile = service.control.get_object(
            'profile',
            client_kwargs={'token': self.token},
            action='get_profile',
            return_object='profile',
            profile_id=self.parsed_token.profile_id,
        )


class PreRunParseTokenFetchProfileMixin(object):

    def pre_run(self, *args, **kwargs):
        self.parsed_token = parse_token(self.token)
        self.profile = service.control.get_object(
            'profile',
            client_kwargs={'token': self.token},
            action='get_profile',
            return_object='profile',
            profile_id=self.parsed_token.profile_id,
        )


class ListGroups(PreRunParseTokenMixin, actions.Action):

    required_fields = ('provider',)

    def run(self, *args, **kwargs):
        # TODO add a test case to ensure that this is instantiated without the mock
        provider = providers.Google(requester_profile=self.profile, organization=self.organization)
        if self.request.HasField('profile_id'):
            for_profile = service.control.get_object(
                'profile',
                client_kwargs={'token': self.token},
                action='get_profile',
                profile_id=self.parsed_token.profile_id,
                return_object='profile',
            )
            groups = provider.list_groups_for_profile(for_profile)
        else:
            groups = provider.list_groups_for_organization()

        self.response.groups.extend(groups)


class JoinGroup(PreRunParseTokenFetchProfileMixin, actions.Action):

    required_fields = ('group_key',)

    def run(self, *args, **kwargs):
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
        )
        group_request = provider.join_group(self.request.group_key)
        group_request.to_protobuf(self.response.request, meta=group_request.get_meta())


class RespondToMembershipRequest(PreRunParseTokenFetchProfileMixin, actions.Action):

    required_fields = ('action', 'request_id')
    type_validators = {
        'request_id': (validators.is_uuid4,),
    }
    field_validators = {
        'request_id': {
            is_valid_membership_request: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        member_request = models.GroupMembershipRequest.objects.get(id=self.request.request_id)
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
        )
        if self.request.action == respond_to_membership_request_pb2.RequestV1.APPROVE:
            provider.approve_request_to_join(member_request)
        else:
            provider.deny_request_to_join(member_request)


class LeaveGroup(PreRunParseTokenMixin, actions.Action):

    required_fields = ('group_key',)

    def run(self, *args, **kwargs):
        provider = providers.Google(requester_profile=self.profile, organization=self.organization)
        provider.leave_group(self.request.group_key)


class ListMembers(PreRunParseTokenFetchProfileMixin, actions.Action):

    required_fields = ('provider', 'group_key')

    def _populate_response_members(self, members):
        members_dict = dict((member.profile.email, member) for member in members)
        profiles = service.control.get_object(
            'profile',
            client_kwargs={'token': self.token},
            action='get_profiles',
            return_object='profiles',
            emails=[x.profile.email for x in members],
        )
        for profile in profiles:
            member = members_dict.get(profile.email)
            if not member:
                # TODO log some error here
                continue
            member.profile.CopyFrom(profile)
            self.response.members.extend([member])

    def run(self, *args, **kwargs):
        provider = providers.Google(requester_profile=self.profile)
        members = provider.list_members_for_group(self.request.group_key, self.request.role)
        if members:
            self._populate_response_members(members)


class GetGroup(PreRunParseTokenMixin, actions.Action):

    required_fields = ('group_key',)

    def run(self, *args, **kwargs):
        provider = providers.Google(requester_profile=self.profile, organization=self.organization)
        group = provider.get_group(self.request.group_key)
        if group:
            self.response.group.CopyFrom(group)


class AddToGroup(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'profile_ids': [validators.is_uuid4_list],
    }
    required_fields = ('group_key',)

    def _fetch_profiles(self):
        client = service.control.Client('profile', token=self.token)
        # TODO add some MAX requirement so we don't have to deal with pagination
        response = client.call_action('get_profiles', ids=self.request.profile_ids)
        return response.result.profiles

    def run(self, *args, **kwargs):
        profiles = self._fetch_profiles()
        provider = providers.Google(requester_profile=self.profile, organization=self.organization)
        members = provider.add_profiles_to_group(profiles, self.request.group_key)
        if members:
            self.response.new_members.extend(members)
