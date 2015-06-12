import httplib2
import logging
import uuid

from apiclient.errors import HttpError
from apiclient.http import BatchHttpRequest
from apiclient.discovery import build
from django.conf import settings
from django.db.models import F
from oauth2client.client import SignedJwtAssertionCredentials
from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.organization.containers import integration_pb2
import service.control

from services.cache import get_redis_client

from .. import (
    base,
    exceptions,
)
from ... import models


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

    def _get_groups_for_profile(self, profile):
        memberships = models.GoogleGroupMember.objects.filter(
            organization_id=self.organization_id,
            profile_id=profile.id,
        ).select_related('group')
        groups = [membership.group for membership in memberships]

        requester_memberships = models.GoogleGroupMember.objects.filter(
            organization_id=self.organization_id,
            profile_id=self.requester_profile.id,
            group_id__in=[group.id for group in groups],
        )
        membership = dict(
            (membership.group_id, membership) for membership in requester_memberships
        )
        return groups, membership

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

    def _get_group(self, group_key):
        # TODO add tests around Http 400 & 403 failure
        return self.directory_client.groups().get(groupKey=group_key).execute()

    def _get_approver_profile_ids(self, group_id):
        roles = map(
            self._get_role_from_role_v1,
            [group_containers.OWNER, group_containers.MANAGER],
        )
        return list(models.GoogleGroupMember.objects.filter(
            group_id=group_id,
            organization_id=self.organization_id,
            role__in=roles,
        ).values_list('profile_id', flat=True))

    def _leave_group(self, group_key):
        removed = True
        try:
            self.directory_client.members().delete(
                groupKey=group_key,
                memberKey=self.requester_profile.email,
            ).execute()
        except HttpError:
            # XXX catch error #sentry
            removed = False
        return removed

    def _add_to_group(self, emails, group_id):
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
                    groupKey=group_id,
                    body={'role': 'MEMBER', 'email': email, 'type': 'USER'},
                ),
                callback=handle_new_member,
            )

        batch.execute(http=self.http)
        return new_members

    def get_groups_settings_and_membership(self, group_keys, fetch_membership=True):
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

    def _get_pending_requests_dict(self, group_ids):
        pending_requests = models.GroupMembershipRequest.objects.filter(
            group_id__in=group_ids,
            provider=group_containers.GOOGLE,
            status=group_containers.PENDING,
            requester_profile_id=self.requester_profile.id,
        ).values('id', 'group_id')
        return dict((req['group_id'], req['id']) for req in pending_requests)

    def _filter_visible_groups(self, groups):
        group_ids = [group.id for group in groups]
        memberships = models.GoogleGroupMember.objects.filter(
            profile_id=self.requester_profile.id,
            organization_id=self.organization_id,
            group_id__in=group_ids,
        )
        membership_dict = dict((membership.group_id, membership) for membership in memberships)

        pending_requests_dict = self._get_pending_requests_dict(group_ids)
        containers = []
        for group in groups:
            container = self.group_to_container(group, membership_dict.get(group.id))
            container.has_pending_request = group.id in pending_requests_dict
            if group.settings.get('showInGroupDirectory', 'false') == 'true':
                containers.append(container)

        return sorted(containers, key=lambda x: x.name)

    def _get_requester_memberships(self, group_ids):
        memberships = models.GoogleGroupMember.objects.filter(
            group_id__in=group_ids,
            profile_id=self.requester_profile.id,
            organization_id=self.organization_id,
        )
        return dict((membership.group_id, membership) for membership in memberships)

    def _add_profiles_to_group(self, profiles, group):
        email_to_profile_dict = dict((profile.email, profile) for profile in profiles)
        id_to_profile_dict = dict((profile.id, profile) for profile in profiles)
        new_members = []

        # TODO add test case for profiles with a different organization_id
        provider_members = self._add_to_group(
            [profile.email for profile in profiles],
            group.provider_uid,
        )
        members = []
        for provider_member in provider_members:
            profile = email_to_profile_dict.get(provider_member['email'])
            if not profile:
                # XXX log an error here #sentry
                continue

            member = models.GoogleGroupMember(
                profile_id=profile.id,
                group_id=group.id,
                role=provider_member['role'],
                organization_id=group.organization_id,
                provider_uid=provider_member['id'],
            )
            members.append(member)

        members = models.GoogleGroupMember.objects.bulk_create(members)
        for member in members:
            profile = id_to_profile_dict.get(member.profile_id)
            if not profile:
                # XXX log an error here #sentry
                continue
            new_members.append(self.google_group_member_to_container(member, profile))
        return new_members

    def can_join_or_can_request(self, group):
        can_join = can_request = False
        if not self.write_access:
            return can_join, can_request

        who_can_join = group.settings.get('whoCanJoin')
        if who_can_join == 'CAN_REQUEST_TO_JOIN':
            can_request = True
        elif who_can_join in ('ANYONE_CAN_JOIN', 'ALL_IN_DOMAIN_CAN_JOIN'):
            can_join = True
        return can_join, can_request

    def can_add_to_group(self, group, membership):
        can_add = False
        if not self.write_access:
            return can_add

        who_can_add = group.settings.get('whoCanInvite')
        if who_can_add == 'ALL_MEMBERS_CAN_INVITE':
            can_add = True
        elif who_can_add == 'ALL_MANAGERS_CAN_INVITE' and self.is_manager(membership):
            can_add = True
        return can_add

    def get_states_for_user_in_group(self, group, membership):
        is_member = is_manager = can_join = can_request = False
        if membership:
            if self.is_manager(membership):
                is_manager = True
            is_member = True
        else:
            can_join, can_request = self.can_join_or_can_request(group)
        return {
            'is_member': is_member,
            'is_manager': is_manager,
            'can_join': can_join,
            'can_request': can_request,
        }

    def is_manager(self, membership):
        return membership and membership.role in ('MANAGER', 'OWNER')

    def is_group_visible(self, group, membership):
        visible = False
        who_can_view_membership = group.settings.get('whoCanViewMembership')
        if who_can_view_membership == 'ALL_IN_DOMAIN_CAN_VIEW':
            visible = True
        elif who_can_view_membership == 'ALL_MEMBERS_CAN_VIEW' and membership:
            visible = True
        elif who_can_view_membership == 'ALL_MANAGERS_CAN_VIEW' and self.is_manager(membership):
            visible = True
        return visible

    def group_to_container(self, group, membership):
        container = group_containers.GroupV1()
        container.id = str(group.id)
        container.name = group.name
        if group.display_name:
            container.display_name = group.display_name

        container.members_count = group.direct_members_count
        container.email = group.email
        if group.description:
            container.group_description = group.description

        states = self.get_states_for_user_in_group(group, membership)
        container.is_member = states.get('is_member', False)
        container.is_manager = states.get('is_manager', False)
        container.can_join = states.get('can_join', False)
        container.can_request = states.get('can_request', False)
        return container

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

    def google_group_member_to_container(self, member, profile):
        container = group_containers.MemberV1()
        container.id = str(member.id)
        # XXX catch this error
        container.role = group_containers.RoleV1.keys().index(member.role)
        container.profile.CopyFrom(profile)
        container.provider_uid = member.provider_uid
        container.group_id = str(member.group_id)
        # NB: this is on the member object but we don't want to risk triggering a group query
        container.provider = group_containers.GOOGLE
        return container

    def get_groups_for_profile(self, profile, **kwargs):
        groups, membership = self._get_groups_for_profile(profile)
        group_ids = [group.id for group in groups]

        pending_requests_dict = self._get_pending_requests_dict(group_ids)
        containers = []
        for group in groups:
            container = self.group_to_container(group, membership.get(group.id))
            container.has_pending_request = group.id in pending_requests_dict
            if self.is_group_visible(group, membership.get(group.id)):
                containers.append(container)
        return sorted(containers, key=lambda x: x.name)

    def get_groups_for_organization(self, **kwargs):
        groups = models.GoogleGroup.objects.filter(organization_id=self.organization_id)
        return self._filter_visible_groups(groups)

    def get_members_for_group(self, group_id, role, **kwargs):
        # TODO catch DoesNotExist
        group = models.GoogleGroup.objects.get(pk=group_id)
        memberships = self._get_requester_memberships([group_id])

        containers = []
        if self.is_group_visible(group, memberships.get(group.pk)):
            members = models.GoogleGroupMember.objects.filter(
                organization_id=self.requester_profile.organization_id,
                group_id=group_id,
                role=self._get_role_from_role_v1(role),
            )
            if not members:
                return []

            profiles = service.control.get_object(
                service='profile',
                action='get_profiles',
                return_object='profiles',
                client_kwargs={'token': self.token},
                ids=[str(member.profile_id) for member in members],
            )
            profiles_dict = dict((
                uuid.UUID(profile.id, version=4),
                profile,
            ) for profile in profiles)
            for member in members:
                profile = profiles_dict.get(member.profile_id)
                if not profile:
                    # TODO log error in #sentry
                    continue

                container = self.google_group_member_to_container(member, profile)
                containers.append(container)
        return containers

    def get_group(self, group_id, **kwargs):
        containers = self.get_groups_with_ids([group_id])
        try:
            return containers[0]
        except IndexError:
            return None

    def get_groups_with_ids(self, group_ids, **kwargs):
        containers = []
        groups = models.GoogleGroup.objects.filter(
            organization_id=self.requester_profile.organization_id,
            id__in=group_ids,
        )
        membership_requests = models.GroupMembershipRequest.objects.filter(
            provider=group_containers.GOOGLE,
            group_id__in=group_ids,
            requester_profile_id=self.requester_profile.id,
            status=group_containers.PENDING,
        ).values_list('group_id', flat=True)
        membership = self._get_requester_memberships(group_ids)
        for group in groups:
            container = self.group_to_container(group, membership.get(group.id))
            container.has_pending_request = group.id in membership_requests
            if (
                not container.is_member and
                group.settings.get('showInGroupDirectory', 'false') == 'false'
            ):
                continue
            containers.append(container)
        return containers

    def add_profiles_to_group(self, profiles, group_id, **kwargs):
        new_members = []
        # TODO catch the DoesNotExist error
        group = models.GoogleGroup.objects.get(pk=group_id)
        memberships = self._get_requester_memberships([group_id])
        if self.can_add_to_group(group, memberships.get(group.id)):
            new_members = self._add_profiles_to_group(profiles, group)
        return new_members

    def join_group(self, group_id, **kwargs):
        # TODO catch DoesNotExist
        group = models.GoogleGroup.objects.get(pk=group_id)
        membership_request = models.GroupMembershipRequest(
            requester_profile_id=self.requester_profile.id,
            status=group_containers.DENIED,
            provider=group_containers.GOOGLE,
            group_id=group_id,
            meta={'whoCanJoin': group.settings.get('whoCanJoin', '')},
        )
        can_join, can_request = self.can_join_or_can_request(group)
        if can_join:
            membership_request.status = group_containers.APPROVED
            self._add_profiles_to_group([self.requester_profile], group)
        elif can_request:
            # TODO raise some error if we don't have any managers to approve
            membership_request.approver_profile_ids = self._get_approver_profile_ids(group_id)
            membership_request.status = group_containers.PENDING

        membership_request.save()
        return membership_request

    def leave_group(self, group_id, **kwargs):
        # TODO catch DoesNotExist, IndexError
        group = models.GoogleGroup.objects.get(pk=group_id)
        removed = self._leave_group(group.provider_uid)
        if removed:
            models.GoogleGroupMember.objects.get(
                group_id=group_id,
                profile_id=self.requester_profile.id,
                organization_id=self.requester_profile.organization_id,
            ).delete()
            group.direct_members_count = F('direct_members_count') - 1
            group.save()

    def approve_request_to_join(self, request, **kwargs):
        # XXX catch does not exist
        member = models.GoogleGroupMember.objects.select_related('group').filter(
            profile_id=self.requester_profile.id,
            group_id=request.group_id,
            organization_id=self.requester_profile.organization_id,
            role__in=['MANAGER', 'OWNER'],
        )
        if not member:
            raise exceptions.Unauthorized('Only a manager can approve a request')

        profile = service.control.get_object(
            service='profile',
            client_kwargs={'token': self.token},
            action='get_profile',
            return_object='profile',
            profile_id=str(request.requester_profile_id),
        )
        self._add_to_group([profile], member[0].group)
        request.status = group_containers.APPROVED
        request.save()
        return request

    def deny_request_to_join(self, request, **kwargs):
        request.status = group_containers.DENIED
        request.save()
        return request
