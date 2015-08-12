from protobufs.services.common import containers_pb2 as common_containers
import service.control

from services import (
    mixins,
    utils,
)

from . import models


class TeamPermissionsMixin(mixins.PreRunParseTokenMixin):

    @property
    def requester_profile(self):
        if not hasattr(self, '_requester_profile'):
            self._requester_profile = service.control.get_object(
                service='profile',
                action='get_profile',
                return_object='profile',
                client_kwargs={'token': self.token},
                profile_id=self.parsed_token.profile_id,
            )
        return self._requester_profile

    def _get_team_id(self):
        try:
            reporting = models.ReportingStructure.objects.values('manager_id').get(
                profile_id=self.requester_profile.id,
                organization_id=self.requester_profile.organization_id,
            )
            team = models.Team.objects.values('id').get(
                manager_profile_id=reporting['manager_id'],
                organization_id=self.requester_profile.organization_id,
            )
        except (models.ReportingStructure.DoesNotExist, models.Team.DoesNotExist):
            return ''
        else:
            return team['id']

    def get_permissions(self, team):
        permissions = common_containers.PermissionsV1()
        if self.parsed_token.is_admin() or self.requester_profile.is_admin:
            permissions.can_edit = True
            permissions.can_add = True
            permissions.can_delete = True
        elif utils.matching_uuids(self._get_team_id(), team.id):
            permissions.can_edit = True
        return permissions


class LocationPermissionsMixin(TeamPermissionsMixin):

    def get_permissions(self, location):
        permissions = common_containers.PermissionsV1()
        if self.parsed_token.is_admin() or self.requester_profile.is_admin:
            permissions.can_edit = True
            permissions.can_add = True
            permissions.can_delete = True
        elif location.members.filter(profile_id=self.parsed_token.profile_id).exists():
            permissions.can_edit = True
        return permissions


class LocationProfileStatsMixin(object):

    def fetch_profile_stats(self, locations):
        client = service.control.Client('profile', token=self.token)
        response = client.call_action(
            'get_profile_stats',
            location_ids=[str(location.id) for location in locations],
        )
        return dict((stat.id, stat.count) for stat in response.result.stats)


class TeamProfileStatsMixin(object):

    def fetch_profile_stats(self, team_ids):
        result = {}
        if team_ids:
            client = service.control.Client('profile', token=self.token)
            response = client.call_action('get_profile_stats', team_ids=team_ids)
            result = dict((stat.id, stat.count) for stat in response.result.stats)
        return result

    def fetch_child_team_counts(self, team_ids):
        result = {}
        if team_ids:
            descendants = service.control.get_object(
                service='organization',
                action='get_team_descendants',
                return_object='descendants',
                client_kwargs={'token': self.token},
                team_ids=team_ids,
                attributes=['id'],
                depth=1,
            )
            for descendant in descendants:
                result[descendant.parent_team_id] = len(descendant.teams)
        return result
