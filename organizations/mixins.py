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
                inflations={'enabled': False},
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
