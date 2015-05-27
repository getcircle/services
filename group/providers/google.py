import httplib2
import json
import os

from apiclient.errors import HttpError
from apiclient.http import BatchHttpRequest
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from protobufs.services.group import containers_pb2 as group_containers
import service.control

from . import (
    base,
    exceptions,
)
from .. import models

# TODO move to settings
SERVICE_ACCOUNT_EMAIL = '1077014421904-v3q3sd1e8n0fq6bgchfv7qul4k9135ur@developer.gserviceaccount.com'
# TODO move to vault or something
SERVICE_ACCOUNT_JSON_FILE = os.path.join(os.path.dirname(__file__), 'Circle-b34aaf973f59.json')
# TODO move to settings
GOOGLE_GROUPS_PROVIDER_SCOPES = (
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.group',
    'https://www.googleapis.com/auth/apps.groups.settings',
)


class Provider(base.BaseGroupsProvider):

    @property
    def http(self):
        if not hasattr(self, '_http'):
            with open(SERVICE_ACCOUNT_JSON_FILE, 'r') as json_key_file:
                json_key = json.load(json_key_file)

            credentials = SignedJwtAssertionCredentials(
                SERVICE_ACCOUNT_EMAIL,
                json_key['private_key'],
                scope=GOOGLE_GROUPS_PROVIDER_SCOPES,
                # XXX this can only be the admin
                sub='michael@circlehq.co',
            )
            self._http = credentials.authorize(httplib2.Http())
        return self._http

    @property
    def directory_client(self):
        if not hasattr(self, '_directory_client'):
            self._directory_client = build('admin', 'directory_v1', http=self.http)
        return self._directory_client

    @property
    def settings_client(self):
        if not hasattr(self, '_settings_client'):
            self._settings_client = build('groupssettings', 'v1', http=self.http)
        return self._settings_client

    def _get_role_from_role_v1(self, role_v1):
        return group_containers.RoleV1.keys()[role_v1]

    def _get_groups(self, email=None):
        if email is not None:
            list_kwargs = {'userKey': email}
        else:
            list_kwargs = {'domain': self.organization.domain}
        # TODO add tests around Http 400 & 403 failures
        # TODO add tests around pagination
        return self.directory_client.groups().list(**list_kwargs).execute()

    def _get_group_members(self, group_key, role):
        # TODO add tests around Http 400 & 403 failure
        # TODO add tests around pagination
        return self.directory_client.members().list(
            groupKey=group_key,
            roles=role,
        ).execute().get('members', [])

    def _get_group_managers(self, group_key):
        roles = ','.join(map(
            self._get_role_from_role_v1,
            [group_containers.OWNER, group_containers.MANAGER],
        ))
        # TODO HttpError tests
        # TODO pagination test
        return self.directory_client.members().list(
            groupKey=group_key,
            roles=roles,
        ).execute().get('members', [])

    def _get_group(self, group_key):
        # TODO add tests around Http 400 & 403 failure
        return self.directory_client.groups().get(groupKey=group_key).execute()

    def _get_approver_profile_ids(self, group_key):
        # XXX should raise an exception here if there are no managers
        managers = self._get_group_managers(group_key)
        client = service.control.Client('profile', token=self.token)
        response = client.call_action(
            'get_profiles',
            emails=[manager['email'] for manager in managers],
        )
        return [profile.id for profile in response.result.profiles]

    def _leave_group(self, group_key):
        try:
            self.directory_client.members().delete(
                groupKey=group_key,
                memberKey=self.requester_profile.email,
            ).execute()
        except HttpError:
            pass

    def _add_to_group(self, emails, group_key):
        new_members = []

        def handle_new_member(request_id, response, exception, **kwargs):
            if response:
                new_members.append(response)

        batch = BatchHttpRequest()
        request_num = 0
        for email in emails:
            request_num += 1
            batch.add(
                self.directory_client.members().insert(
                    groupKey=group_key,
                    body={'role': 'MEMBER', 'email': email, 'type': 'USER'},
                ),
                callback=handle_new_member,
            )

        batch.execute(http=self.http)
        return new_members

    def _get_groups_settings_and_membership(self, group_keys, fetch_membership=True):
        groups_settings = {}
        membership = {}

        def handle_is_member(request_id, response, exception, **kwargs):
            request_num, group = request_id.split('::')
            if response:
                membership[group] = response

        def handle_groups_settings(request_id, response, exception, **kwargs):
            if response:
                groups_settings[response['email']] = response

        batch = BatchHttpRequest()
        request_num = 0
        for group_key in group_keys:
            request_num += 1
            batch.add(
                self.settings_client.groups().get(groupUniqueId=group_key),
                callback=handle_groups_settings,
            )
            if fetch_membership:
                request_num += 1
                batch.add(
                    self.directory_client.members().get(
                        memberKey=self.requester_profile.email,
                        groupKey=group_key,
                    ),
                    callback=handle_is_member,
                    request_id='%s::%s' % (request_num, group_key),
                )

        batch.execute(http=self.http)
        return groups_settings, membership

    def can_join(self, group_key, group_settings):
        can_join = False
        who_can_join = group_settings.get('whoCanJoin')
        if who_can_join == 'CAN_REQUEST_TO_JOIN':
            can_join = True
        elif who_can_join in ('ANYONE_CAN_JOIN', 'ALL_IN_DOMAIN_CAN_JOIN'):
            can_join = True
        return can_join

    def can_add_to_group(self, group_key, group_settings, membership):
        can_add = False
        who_can_add = group_settings.get('whoCanInvite')
        role = membership.get(group_key, {}).get('role')
        if who_can_add == 'ALL_MEMBERS_CAN_INVITE':
            can_add = True
        elif who_can_add == 'ALL_MANAGERS_CAN_INVITE' and role in ('OWNER', 'MANAGER'):
            can_add = True
        return can_add

    def can_join_without_approval(self, group_key, group_settings):
        return group_settings.get('whoCanJoin') in ('ANYONE_CAN_JOIN', 'ALL_IN_DOMAIN_CAN_JOIN')

    def is_member_or_can_join(self, group_key, group_settings, membership):
        is_member = can_join = False
        if group_key in membership:
            is_member = True
        else:
            can_join = self.can_join(group_key, group_settings)
        return is_member, can_join

    def is_group_visible(self, group_key, group_settings, membership):
        visible = False
        who_can_view_membership = group_settings.get('whoCanViewMembership')
        role = membership.get(group_key, {}).get('role', False)
        if who_can_view_membership == 'ALL_IN_DOMAIN_CAN_VIEW':
            visible = True
        elif who_can_view_membership == 'ALL_MEMBERS_CAN_VIEW' and role:
            visible = True
        elif who_can_view_membership == 'ALL_MANAGERS_CAN_VIEW' and role in ('MANAGER', 'OWNER'):
            visible = True
        return visible

    def provider_group_to_container(self, provider_group):
        group = group_containers.GroupV1()
        group.id = provider_group['id']
        group.name = provider_group['name']
        group.members_count = int(provider_group['directMembersCount'])
        group.email = provider_group['email']
        return group

    def provider_member_to_container(self, provider_member, profile=None):
        member = group_containers.MemberV1()
        member.id = provider_member['id']
        member.role = group_containers.RoleV1.keys().index(provider_member['role'])
        if profile:
            member.profile.CopyFrom(profile)
        else:
            member.profile.email = provider_member['email']
        return member

    def list_groups_for_profile(self, profile, **kwargs):
        provider_groups = self._get_groups(profile.email)
        group_keys = [x['email'] for x in provider_groups['groups']]
        groups_settings, membership = self._get_groups_settings_and_membership(group_keys)

        groups = []
        for provider_group in provider_groups['groups']:
            group_key = provider_group['email']
            group_settings = groups_settings.get(group_key, {})
            group = self.provider_group_to_container(provider_group)
            group.is_member, group.can_join = self.is_member_or_can_join(
                group_key,
                group_settings,
                membership,
            )

            if self.is_group_visible(group_key, group_settings, membership):
                groups.append(group)
        return sorted(groups, key=lambda x: x.name)

    def list_groups_for_organization(self, **kwargs):
        provider_groups = self._get_groups()
        group_keys = [x['email'] for x in provider_groups['groups']]
        groups_settings, _ = self._get_groups_settings_and_membership(
            group_keys,
            fetch_membership=False,
        )

        groups = []
        for provider_group in provider_groups['groups']:
            group = self.provider_group_to_container(provider_group)
            group_settings = groups_settings.get(provider_group['email'], {})
            if group_settings.get('showInGroupDirectory', False):
                groups.append(group)
        return sorted(groups, key=lambda x: x.name)

    def list_members_for_group(self, group_key, role, **kwargs):
        groups_settings, membership = self._get_groups_settings_and_membership([group_key])
        # TODO handle case where the group doesn't exist
        if not groups_settings:
            return []

        group_settings = groups_settings.values()[0]
        provider_role = self._get_role_from_role_v1(role)

        members = []
        if self.is_group_visible(group_key, group_settings, membership):
            provider_members = self._get_group_members(group_key, provider_role)
            for provider_member in provider_members:
                member = self.provider_member_to_container(provider_member)
                members.append(member)
        return members

    def get_group(self, group_key, **kwargs):
        provider_group = self._get_group(group_key)
        group_settings, _ = self._get_groups_settings_and_membership(
            [group_key],
            fetch_membership=False,
        )
        group_settings = group_settings.values()[0]
        group = None
        if group_settings.get('showInGroupDirectory', False):
            group = self.provider_group_to_container(provider_group)
        return group

    def add_profiles_to_group(self, profiles, group_key, **kwargs):
        new_members = []

        profiles_dict = dict((profile.email, profile) for profile in profiles)
        groups_settings, membership = self._get_groups_settings_and_membership([group_key])
        # TODO handle case where group doesn't exist
        group_settings = groups_settings.values()[0]
        if self.can_add_to_group(group_key, group_settings, membership):
            # TODO add test case for profiles with a different organization_id
            provider_members = self._add_to_group(
                [profile.email for profile in profiles],
                group_key,
            )
            for member in provider_members:
                profile = profiles_dict.get(member['email'])
                if not profile:
                    continue
                new_members.append(self.provider_member_to_container(member, profile=profile))
        return new_members

    def join_group(self, group_key, **kwargs):
        group_settings, _ = self._get_groups_settings_and_membership(
            [group_key],
            fetch_membership=False,
        )
        group_settings = group_settings.values()[0]

        membership_request = models.GroupMembershipRequest(
            requester_profile_id=self.requester_profile.id,
            status=group_containers.DENIED,
            provider=group_containers.GOOGLE,
            group_key=group_key,
            meta={'whoCanJoin': group_settings.get('whoCanJoin', '')},
        )
        if self.can_join_without_approval(group_key, group_settings):
            membership_request.status = group_containers.APPROVED
        elif self.can_join(group_key, group_settings):
            # TODO raise some error if we don't have any managers to approve
            membership_request.approver_profile_ids = self._get_approver_profile_ids(group_key)
            membership_request.status = group_containers.PENDING

        membership_request.save()
        return membership_request

    def leave_group(self, group_key, **kwargs):
        self._leave_group(group_key)

    def approve_request_to_join(self, request, **kwargs):
        managers = self._get_group_managers(request.group_key)
        manager_emails = [manager['email'] for manager in managers]
        if self.requester_profile.email not in manager_emails:
            raise exceptions.Unauthorized('Only a manager can approve a request')

        profile = service.control.get_object(
            service='profile',
            client_kwargs={'token': self.token},
            action='get_profile',
            return_object='profile',
            profile_id=request.requester_profile_id,
        )
        self._add_to_group([profile.email], request.group_key)
        request.status = group_containers.APPROVED
        request.save()
        return request

    def deny_request_to_join(self, request, **kwargs):
        request.status = group_containers.DENIED
        request.save()
        return request
