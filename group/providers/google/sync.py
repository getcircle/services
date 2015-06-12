import datetime
import logging
import uuid

from cacheops import invalidate_model

# XXX remove this
from profiles import models as profile_models

from ... import models


class Sync(object):

    def __init__(self, provider, *args, **kwargs):
        self.sync_id = uuid.uuid4()
        self.provider = provider
        self.organization_id = self.provider.organization.id
        super(Sync, self).__init__(*args, **kwargs)

    @property
    def logger(self):
        return logging.getLogger('groups:google:sync')

    def sync_groups(self):
        self.logger.info('starting groups sync: %s', self.sync_id)
        in_progress = True
        page_token = None
        while in_progress:
            # XXX should probably have these referencing functions of the
            # provider instead of accessing directory_client driectly
            response = self.provider.directory_client.groups().list(
                domain=self.provider.organization.domain,
                pageToken=page_token,
            ).execute()
            self._sync_groups(response['groups'])
            if 'nextPageToken' in response:
                page_token = response['nextPageToken']
                in_progress = True
            else:
                in_progress = False
        self._clear_stale_groups()
        self._clear_cacheops()

    def _sync_groups(self, provider_groups):
        groups = []
        for provider_group in provider_groups:
            # XXX catch and log this KeyError
            group = models.GoogleGroup(
                provider_uid=provider_group['id'],
                email=provider_group['email'],
                name=provider_group['name'],
                direct_members_count=int(provider_group['directMembersCount']),
                description=provider_group['description'] or None,
                aliases=provider_group.get('aliases'),
                last_sync_id=self.sync_id,
                organization_id=self.organization_id,
                changed=datetime.datetime.now(),
            )
            groups.append(group)

        groups = self._save_or_update_groups(groups)
        self._sync_settings(groups)
        for group in groups:
            self._sync_group_members(group)

    def _save_or_update_groups(self, groups):
        groups_to_save = []
        groups_to_update = []
        existing_groups = list(models.GoogleGroup.objects.filter(
        ).values_list('provider_uid', flat=True))
        existing_groups = dict(models.GoogleGroup.objects.filter(
            provider_uid__in=[group.provider_uid for group in groups],
        ).values_list('provider_uid', 'id'))
        for group in groups:
            if group.provider_uid in existing_groups:
                group.id = existing_groups[group.provider_uid]
                groups_to_update.append(group)
            else:
                groups_to_save.append(group)

        if groups_to_save:
            models.GoogleGroup.objects.bulk_create(groups_to_save)

        if groups_to_update:
            models.GoogleGroup.bulk_update_manager.bulk_update(
                groups_to_update,
                exclude_fields=['settings', 'created', 'organization_id', 'id'],
            )
        return models.GoogleGroup.objects.filter(
            organization_id=self.organization_id,
            last_sync_id=self.sync_id,
        )

    def _sync_settings(self, groups):
        if not groups:
            # XXX log an error to #sentry
            return False
        # XXX should be a public method on provider?
        # XXX batch this up into smaller groups so google doesn't complain
        groups_settings, _ = self.provider.get_groups_settings_and_membership(
            [group.email for group in groups],
            fetch_membership=False,
        )
        groups_to_update = []
        for group in groups:
            group_settings = groups_settings.get(group.email)
            if not group_settings:
                continue

            # hstore values must be strings
            for key, value in group_settings.iteritems():
                if not isinstance(value, basestring):
                    group_settings[key] = str(value)
            group.settings = group_settings
            groups_to_update.append(group)

        if groups_to_update:
            models.GoogleGroup.bulk_update_manager.bulk_update(
                groups_to_update,
                update_fields=['settings'],
            )

    def _clear_stale_groups(self):
        # XXX clear out stale members as well
        stale_groups = models.GoogleGroup.objects.filter(
            organization_id=self.organization_id,
        ).exclude(last_sync_id=self.sync_id)
        self.logger.info(
            'removing %s stale google groups not matching sync_id: %s',
            len(stale_groups),
            self.sync_id,
        )
        stale_groups.delete()

    def _sync_group_members(self, group):
        in_progress = True
        page_token = None
        while in_progress:
            response = self.provider.directory_client.members().list(
                groupKey=group.provider_uid,
                pageToken=page_token,
            ).execute()
            self._save_or_update_members(response.get('members', []), group)
            if 'nextPageToken' in response:
                page_token = response['nextPageToken']
            else:
                in_progress = False

    def _save_or_update_members(self, provider_members, group):
        member_emails = filter(None, [member.get('email') for member in provider_members])
        profiles_dict = dict(profile_models.Profile.objects.filter(
            email__in=member_emails,
        ).values_list('email', 'id'))
        existing_members = models.GoogleGroupMember.objects.filter(
            group_id=group.id,
            organization_id=self.organization_id,
        )
        existing_members_dict = dict((member.profile_id, member) for member in existing_members)

        members_to_save = []
        members_to_update = []
        for provider_member in provider_members:
            profile_id = profiles_dict.get(provider_member.get('email'))
            if not profile_id:
                self.logger.error('profile not found for: %s', provider_member)
                continue

            if profile_id in existing_members_dict:
                member = existing_members_dict[profile_id]
                member.role = provider_member['role']
                member.last_sync_id = self.sync_id
                member.changed = datetime.datetime.now()
                members_to_update.append(member)
                member.provider_uid = provider_member['id']
            else:
                member = models.GoogleGroupMember(
                    profile_id=profile_id,
                    group_id=group.id,
                    role=provider_member['role'],
                    organization_id=self.organization_id,
                    last_sync_id=self.sync_id,
                    provider_uid=provider_member['id'],
                )
                members_to_save.append(member)

        models.GoogleGroupMember.objects.bulk_create(members_to_save)
        if members_to_update:
            models.GoogleGroupMember.bulk_update_manager.bulk_update(members_to_update)

    def _clear_cacheops(self):
        invalidate_model(models.GoogleGroup)
        invalidate_model(models.GoogleGroupMember)
