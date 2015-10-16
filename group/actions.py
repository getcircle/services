from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.group.actions import respond_to_membership_request_pb2
from protobufs.services.organization.containers import integration_pb2
from protobufs.services.notification import containers_pb2 as notification_containers
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
        self.profile = service.control.get_object(
            'profile',
            client_kwargs={'token': self.token},
            action='get_profile',
            return_object='profile',
            profile_id=self.parsed_token.profile_id,
        )
        self.integration = service.control.get_object(
            service='organization',
            action='get_integration',
            return_object='integration',
            client_kwargs={'token': self.token},
            integration_type=integration_pb2.GOOGLE_GROUPS,
        )


class GetGroups(PreRunParseTokenMixin, actions.Action):

    required_fields = ('provider',)

    def run(self, *args, **kwargs):
        # TODO add a test case to ensure that this is instantiated without the mock
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
            integration=self.integration,
        )
        if self.request.HasField('profile_id'):
            for_profile = service.control.get_object(
                'profile',
                client_kwargs={'token': self.token},
                action='get_profile',
                profile_id=self.request.profile_id,
                return_object='profile',
            )
            groups = provider.get_groups_for_profile(
                for_profile,
                paginator=self.control.paginator,
            )
        else:
            groups = provider.get_groups_for_organization(
                paginator=self.control.paginator,
            )

        self.paginated_response(
            self.response.groups,
            groups,
            lambda item, container: container.extend([item]),
        )


class JoinGroup(PreRunParseTokenMixin, actions.Action):

    required_fields = ('group_id', 'provider')

    def _send_notification(self, membership_request):
        # XXX log to #sentry
        if not membership_request.approver_profile_ids:
            return False

        if membership_request.status == group_containers.PENDING:
            try:
                service.control.call_action(
                    service='notification',
                    action='send_notification',
                    client_kwargs={'token': self.token},
                    to_profile_ids=map(str, membership_request.approver_profile_ids),
                    notification={
                        'notification_type_id': (
                            notification_containers.NotificationTypeV1.GOOGLE_GROUPS
                        ),
                        # TODO write tests around these notifications
                        'group_membership_request': {
                            'group_id': membership_request.group_id,
                            'provider': membership_request.provider,
                            'requester_profile_id': membership_request.requester_profile_id,
                            'request_id': str(membership_request.id),
                        },
                    },
                )
            except service.control.CallActionError:
                # TODO log error
                pass

    def run(self, *args, **kwargs):
        # TODO switch on self.request.provider
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
            integration=self.integration,
        )
        membership_request = provider.join_group(self.request.group_id)
        self._send_notification(membership_request)
        membership_request.to_protobuf(self.response.request, meta=membership_request.get_meta())


class RespondToMembershipRequest(PreRunParseTokenMixin, actions.Action):

    required_fields = ('action', 'request_id')
    type_validators = {
        'request_id': (validators.is_uuid4,),
    }
    field_validators = {
        'request_id': {
            is_valid_membership_request: 'DOES_NOT_EXIST',
        },
    }

    def _send_notification(self, membership_request):
        try:
            service.control.call_action(
                service='notification',
                action='send_notification',
                client_kwargs={'token': self.token},
                to_profile_ids=[str(membership_request.requester_profile_id)],
                notification={
                    'notification_type_id': (
                        notification_containers.NotificationTypeV1.GOOGLE_GROUPS
                    ),
                    'group_membership_request_response': {
                        'group_id': str(membership_request.group_id),
                        'provider': membership_request.provider,
                        'group_manager_profile_id': str(self.profile.id),
                        'approved': membership_request.status == group_containers.APPROVED,
                    },
                },
            )
        except service.control.CallActionError:
            # TODO log error
            pass

    def run(self, *args, **kwargs):
        membership_request = models.GroupMembershipRequest.objects.get(id=self.request.request_id)
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
            integration=self.integration,
        )
        if self.request.action == respond_to_membership_request_pb2.RequestV1.APPROVE:
            membership_request = provider.approve_request_to_join(membership_request)
        else:
            membership_request = provider.deny_request_to_join(membership_request)

        self._send_notification(membership_request)


class LeaveGroup(PreRunParseTokenMixin, actions.Action):

    required_fields = ('group_id', 'provider')

    def run(self, *args, **kwargs):
        # XXX switch on self.request.provider
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
            integration=self.integration,
        )
        provider.leave_group(self.request.group_id)


class GetMembers(PreRunParseTokenMixin, actions.Action):

    required_fields = ('provider', 'group_id')
    type_validators = {
        'group_id': (validators.is_uuid4,),
    }

    def run(self, *args, **kwargs):
        # TODO switch on provider
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
            integration=self.integration,
            paginator=self.control.paginator,
        )
        members = provider.get_members_for_group(self.request.group_id, self.request.role)
        self.response.members.extend(members)


class GetGroup(PreRunParseTokenMixin, actions.Action):

    required_fields = ('group_id', 'provider')

    def run(self, *args, **kwargs):
        # TODO switch on self.request.provider
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
            integration=self.integration,
        )
        group = provider.get_group(self.request.group_id)
        if not group:
            raise self.ActionFieldError('group_id', 'DOES_NOT_EXIST')
        self.response.group.CopyFrom(group)


class AddToGroup(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'profile_ids': [validators.is_uuid4_list],
    }
    required_fields = ('group_id', 'provider')

    def _fetch_profiles(self):
        client = service.control.Client('profile', token=self.token)
        # TODO add some MAX requirement so we don't have to deal with pagination
        response = client.call_action('get_profiles', ids=self.request.profile_ids)
        return response.result.profiles

    def run(self, *args, **kwargs):
        profiles = self._fetch_profiles()
        # TODO switch on self.request.provider
        provider = providers.Google(
            requester_profile=self.profile,
            token=self.token,
            integration=self.integration,
        )
        members = provider.add_profiles_to_group(profiles, self.request.group_id)
        if members:
            self.response.new_members.extend(members)


class GetMembershipRequests(PreRunParseTokenMixin, actions.Action):

    def run(self, *args, **kwargs):
        request_kwargs = {
            'approver_profile_ids__contains': [self.profile.id],
        }
        if self.request.HasField('status'):
            request_kwargs['status'] = self.request.status

        requests = models.GroupMembershipRequest.objects.filter(**request_kwargs)
        self.paginated_response(
            self.response.requests,
            requests,
            lambda item, container: item.to_protobuf(container.add(), meta=item.get_meta()),
        )
