from protobuf_to_dict import protobuf_to_dict
from protobufs.services.team import containers_pb2 as team_containers
from service import (
    actions,
    validators,
)
import service.control
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


class GetMembers(PreRunParseTokenMixin, actions.Action):

    required_fields = ('team_id',)
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        exists = models.Team.objects.filter(
            pk=self.request.team_id,
            organization_id=self.parsed_token.organization_id,
        ).exists()
        if not exists:
            raise self.ActionFieldError('team_id', 'DOES_NOT_EXIST')

        members = models.TeamMember.objects.filter(
            organization_id=self.parsed_token.organization_id,
            team_id=self.request.team_id,
            role=self.request.role,
        )
        profile_ids = [str(member.profile_id) for member in self.get_paginated_objects(members)]
        profiles = service.control.get_object(
            service='profile',
            action='get_profiles',
            client_kwargs={'token': self.token},
            control={'paginator': {'page_size': len(profile_ids)}},
            return_object='profiles',
            ids=profile_ids,
            inflations={'disabled': True},
        )
        profile_id_to_profile = dict((p.id, p) for p in profiles)
        for member in members:
            container = self.response.members.add()
            profile = profile_id_to_profile[str(member.profile_id)]
            member.to_protobuf(
                container,
                profile=protobuf_to_dict(profile),
            )
