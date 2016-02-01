from protobufs.services.team import containers_pb2 as team_containers
from service import (
    actions,
    validators,
)
from services.mixins import PreRunParseTokenMixin

from ..actions import (
    add_members,
    create_team,
    get_permissions_for_team,
    get_team,
)
from .. import models


class CreateTeam(PreRunParseTokenMixin, actions.Action):

    required_fields = ('team', 'team.name',)

    def run(self, *args, **kwargs):
        team = create_team(
            container=self.request.team,
            token=self.token,
            by_profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
        )
        team.to_protobuf(self.response.team)
        coordinator = team_containers.TeamMemberV1(
            role=team_containers.TeamMemberV1.COORDINATOR,
            profile_id=self.parsed_token.profile_id,
        )
        add_members([coordinator], team.id, organization_id=self.parsed_token.organization_id)


class AddMembers(PreRunParseTokenMixin, actions.Action):

    required_fields = ('team_id', 'members',)
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        exists = models.Team.objects.filter(
            organization_id=self.parsed_token.organization_id,
            pk=self.request.team_id,
        )
        if not exists:
            raise self.ActionFieldError('team_id', 'DOES_NOT_EXIST')

        add_members(
            self.request.members,
            self.request.team_id,
            organization_id=self.parsed_token.organization_id,
        )


class GetTeam(PreRunParseTokenMixin, actions.Action):

    required_fields = ('team_id',)
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            team = get_team(
                team_id=self.request.team_id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.Team.DoesNotExist:
            raise self.ActionFieldError('team_id', 'DOES_NOT_EXIST')
        team.to_protobuf(self.response.team, inflations=self.request.inflations, token=self.token)
        is_member, permissions = get_permissions_for_team(
            team_id=team.id,
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        self.response.is_member = is_member
        self.response.team.permissions.CopyFrom(permissions)
