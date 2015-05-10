import httplib2
import json

from apiclient.http import BatchHttpRequest
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from protobufs.services.group import containers_pb2 as group_containers

from . import base

# TODO move to settings
SERVICE_ACCOUNT_EMAIL = '1077014421904-v3q3sd1e8n0fq6bgchfv7qul4k9135ur@developer.gserviceaccount.com'
# TODO move to vault or something
SERVICE_ACCOUNT_JSON_FILE = '/Users/mhahn/labs/services/Circle-b34aaf973f59.json'
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
                sub=self.requester_profile.email,
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

    def _get_group_members(self, group_email, role):
        # TODO add tests around Http 400 & 403 failure
        # TODO add tests around pagination
        return self.directory_client.members().list(groupKey=group_email, roles=role).execute()

    def _get_groups_settings_and_membership(self, group_emails, fetch_membership=True):
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
        for group_email in group_emails:
            request_num += 1
            batch.add(
                self.settings_client.groups().get(groupUniqueId=group_email),
                callback=handle_groups_settings,
            )
            if fetch_membership:
                request_num += 1
                batch.add(
                    self.directory_client.members().get(
                        memberKey=self.requester_profile.email,
                        groupKey=group_email,
                    ),
                    callback=handle_is_member,
                    request_id='%s::%s' % (request_num, group_email),
                )

        batch.execute(http=self.http)
        return groups_settings, membership

    def is_member_or_can_join(self, group_email, group_settings, membership):
        is_member = can_join = False
        if group_email in membership:
            is_member = True
        else:
            who_can_join = group_settings.get('whoCanJoin')
            if who_can_join == 'CAN_REQUEST_TO_JOIN':
                can_join = True
            elif who_can_join in ('ANYONE_CAN_JOIN', 'ALL_IN_DOMAIN_CAN_JOIN'):
                can_join = True
        return is_member, can_join

    def is_group_visible(self, group_email, group_settings, membership):
        visible = False
        who_can_view_membership = group_settings.get('whoCanViewMembership')
        role = membership.get(group_email, {}).get('role', False)
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

    def list_groups_for_profile(self, profile, **kwargs):
        provider_groups = self._get_groups(profile.email)
        group_emails = [x['email'] for x in provider_groups['groups']]
        groups_settings, membership = self._get_groups_settings_and_membership(group_emails)

        groups = []
        for provider_group in provider_groups['groups']:
            group_email = provider_group['email']
            group_settings = groups_settings.get(group_email, {})
            group = self.provider_group_to_container(provider_group)
            group.is_member, group.can_join = self.is_member_or_can_join(
                group_email,
                group_settings,
                membership,
            )

            if self.is_group_visible(group_email, group_settings, membership):
                groups.append(group)
        return groups

    def list_groups_for_organization(self, **kwargs):
        provider_groups = self._get_groups()
        group_emails = [x['email'] for x in provider_groups['groups']]
        groups_settings, _ = self._get_groups_settings_and_membership(
            group_emails,
            fetch_membership=False,
        )

        groups = []
        for provider_group in provider_groups['groups']:
            group = self.provider_group_to_container(provider_group)
            group_settings = groups_settings.get(provider_group['email'], {})
            if group_settings.get('showInGroupDirectory', False):
                groups.append(group)
        return groups

    def list_members_for_group(self, group_email, role, **kwargs):
        groups_settings, membership = self._get_groups_settings_and_membership([group_email])
        group_settings = groups_settings.values()[0]
        provider_role = self._get_role_from_role_v1(role)

        members = []
        if self.is_group_visible(group_email, group_settings, membership):
            members = self._get_group_members(group_email, provider_role)
        return members
