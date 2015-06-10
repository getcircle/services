import httplib2
import logging

from apiclient.errors import HttpError
from apiclient.http import BatchHttpRequest
from apiclient.discovery import build
from django.conf import settings
from oauth2client.client import SignedJwtAssertionCredentials
from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.organization.containers import integration_pb2
import service.control

from services.cache import get_redis_client

from . import (
    base,
    exceptions,
)
from .. import models


class Provider(base.BaseGroupsProvider):

    @property
    def logger(self):
        return logging.getLogger('groups:google')

    @property
    def http(self):
        if not hasattr(self, '_http'):
            integration = service.control.get_object(
                service='organization',
                action='get_integration',
                return_object='integration',
                client_kwargs={'token': self.token},
                integration_type=integration_pb2.GOOGLE_GROUPS,
            )
            for scope in integration.google_groups.scopes:
                if scope.endswith('readonly'):
                    self.write_access = False
                    break

            credentials = SignedJwtAssertionCredentials(
                settings.GOOGLE_ADMIN_SDK_JSON_KEY.get('client_email'),
                settings.GOOGLE_ADMIN_SDK_JSON_KEY.get('private_key'),
                scope=integration.google_groups.scopes,
                sub=integration.google_groups.admin_email,
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

    def _get_next_page_cache_key(self, request_key):
        return 'groups:google:paginator:%s' % (request_key,)

    def _map_next_page_token(self, paginator, next_page_token, request_key):
        if not next_page_token:
            paginator.ClearField('next_page')
            self._clear_next_page_mapping(request_key)
            return

        cache_key = self._get_next_page_cache_key(request_key)
        redis_client = get_redis_client()
        # default the next page to 1
        redis_client.hsetnx(cache_key, 'next_page', 1)

        page_number = redis_client.hincrby(cache_key, 'next_page', 1)
        redis_client.hset(cache_key, page_number, next_page_token)
        paginator.next_page = page_number

    def _get_page_token(self, page_number, request_key):
        cache_key = self._get_next_page_cache_key(request_key)
        redis_client = get_redis_client()
        return redis_client.hget(cache_key, page_number)

    def _clear_next_page_mapping(self, request_key):
        cache_key = self._get_next_page_cache_key(request_key)
        redis_client = get_redis_client()
        redis_client.delete(cache_key)

    def _get_groups(self, request_key, email=None, paginator=None):
        if email is not None:
            list_kwargs = {'userKey': email}
        else:
            list_kwargs = {'domain': self.organization.domain}

        if paginator is not None:
            list_kwargs['maxResults'] = paginator.page_size
            if paginator.next_page:
                token = self._get_page_token(paginator.page, request_key)
                list_kwargs['pageToken'] = token
            elif paginator.page == 1:
                self._clear_next_page_mapping(request_key)

        # TODO add tests around Http 400 & 403 failures
        # TODO add tests around pagination
        response = self.directory_client.groups().list(**list_kwargs).execute()
        if paginator is not None:
            next_page_token = response.get('nextPageToken', 0)
            self._map_next_page_token(paginator, next_page_token, request_key)
        return response

    def _get_groups_with_keys(self, keys):
        groups = []

        def handle_group(request_id, response, exception, **kwargs):
            if exception is not None:
                self.logger.error('Error fetching group: %s', exception)
                return False
            groups.append(response)

        batch = BatchHttpRequest()
        request_num = 0
        for key in keys:
            request_num += 1
            batch.add(
                self.directory_client.groups().get(
                    groupKey=key,
                ),
                callback=handle_group,
            )

        batch.execute(http=self.http)
        return groups

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
            if exception is not None:
                self.logger.error('Error adding new member: %s', exception)
                return False
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
            if response:
                request_num, group = request_id.split('::')
                membership[group] = response

        def handle_groups_settings(request_id, response, exception, **kwargs):
            if exception is not None:
                self.logger.error('Error fetching group settings: %s', exception)
                return False
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

    def _get_pending_requests_dict(self, group_keys):
        pending_requests = models.GroupMembershipRequest.objects.filter(
            group_key__in=group_keys,
            provider=group_containers.GOOGLE,
            status=group_containers.PENDING,
            requester_profile_id=self.requester_profile.id,
        ).values('id', 'group_key')
        return dict((req['group_key'], req['id']) for req in pending_requests)

    def _filter_visible_groups(self, provider_groups):
        group_keys = [x['email'] for x in provider_groups['groups']]
        groups_settings, membership = self._get_groups_settings_and_membership(group_keys)

        pending_requests_dict = self._get_pending_requests_dict(group_keys)
        groups = []
        for provider_group in provider_groups['groups']:
            group_settings = groups_settings.get(provider_group['email'], {})
            group = self.provider_group_to_container(provider_group, group_settings, membership)
            group.has_pending_request = provider_group['email'] in pending_requests_dict
            if group_settings.get('showInGroupDirectory', 'false') == 'true':
                groups.append(group)

        return sorted(groups, key=lambda x: x.name)

    def can_join_or_can_request(self, group_key, group_settings):
        can_join = can_request = False
        if not self.write_access:
            return can_join, can_request

        who_can_join = group_settings.get('whoCanJoin')
        if who_can_join == 'CAN_REQUEST_TO_JOIN':
            can_request = True
        elif who_can_join in ('ANYONE_CAN_JOIN', 'ALL_IN_DOMAIN_CAN_JOIN'):
            can_join = True
        return can_join, can_request

    def can_add_to_group(self, group_key, group_settings, membership):
        can_add = False
        if not self.write_access:
            return can_add

        who_can_add = group_settings.get('whoCanInvite')
        if who_can_add == 'ALL_MEMBERS_CAN_INVITE':
            can_add = True
        elif who_can_add == 'ALL_MANAGERS_CAN_INVITE' and self.is_manager(group_key, membership):
            can_add = True
        return can_add

    def get_states_for_user_in_group(self, group_key, group_settings, membership):
        is_member = is_manager = can_join = can_request = False
        if group_key in membership:
            if self.is_manager(group_key, membership):
                is_manager = True
            is_member = True
        else:
            can_join, can_request = self.can_join_or_can_request(group_key, group_settings)
        return {
            'is_member': is_member,
            'is_manager': is_manager,
            'can_join': can_join,
            'can_request': can_request,
        }

    def is_manager(self, group_key, membership):
        return membership.get(group_key, {}).get('role') in ('MANAGER', 'OWNER')

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

    def provider_group_to_container(self, provider_group, group_settings, membership):
        group = group_containers.GroupV1()
        group.id = provider_group['id']
        group.name = provider_group['name']
        group.members_count = int(provider_group['directMembersCount'])
        group.email = provider_group['email']
        group.group_description = provider_group['description']

        states = self.get_states_for_user_in_group(
            provider_group['email'],
            group_settings,
            membership,
        )
        group.is_member = states.get('is_member', False)
        group.is_manager = states.get('is_manager', False)
        group.can_join = states.get('can_join', False)
        group.can_request = states.get('can_request', False)
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

    def get_groups_for_profile(self, profile, paginator=None, request_key=None, **kwargs):
        provider_groups = self._get_groups(
            request_key=request_key,
            email=profile.email,
            paginator=paginator,
        )
        group_keys = [x['email'] for x in provider_groups['groups']]
        groups_settings, membership = self._get_groups_settings_and_membership(group_keys)

        pending_requests_dict = self._get_pending_requests_dict(group_keys)

        groups = []
        for provider_group in provider_groups['groups']:
            group_key = provider_group['email']
            group_settings = groups_settings.get(group_key, {})
            group = self.provider_group_to_container(provider_group, group_settings, membership)
            group.has_pending_request = group_key in pending_requests_dict
            if self.is_group_visible(group_key, group_settings, membership):
                groups.append(group)
        return sorted(groups, key=lambda x: x.name)

    def get_groups_for_organization(self, paginator=None, request_key=None, **kwargs):
        provider_groups = self._get_groups(request_key=request_key, paginator=paginator)
        return self._filter_visible_groups(provider_groups)

    def get_members_for_group(self, group_key, role, **kwargs):
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

    def get_groups_with_keys(self, keys, **kwargs):
        provider_groups = self._get_groups_with_keys(keys)
        return self._filter_visible_groups(provider_groups)

    def get_group(self, group_key, **kwargs):
        provider_group = self._get_group(group_key)
        group_settings, membership = self._get_groups_settings_and_membership(
            [provider_group['email']],
        )
        group_settings = group_settings.values()[0]
        group = None
        if group_settings.get('showInGroupDirectory', 'false') == 'true':
            group = self.provider_group_to_container(provider_group, group_settings, membership)
            if not group.is_member and group.can_request:
                group.has_pending_request = models.GroupMembershipRequest.objects.filter(
                    provider=group_containers.GOOGLE,
                    group_key=group.email,
                    requester_profile_id=self.requester_profile.id,
                    status=group_containers.PENDING,
                ).exists()
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
        can_join, can_request = self.can_join_or_can_request(group_key, group_settings)
        if can_join:
            membership_request.status = group_containers.APPROVED
            self._add_to_group([self.requester_profile.email], group_key)
        elif can_request:
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
            profile_id=str(request.requester_profile_id),
        )
        self._add_to_group([profile.email], request.group_key)
        request.status = group_containers.APPROVED
        request.save()
        return request

    def deny_request_to_join(self, request, **kwargs):
        request.status = group_containers.DENIED
        request.save()
        return request
