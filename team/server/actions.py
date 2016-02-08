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
    remove_members,
    update_members,
    update_team,
)
from .. import models


class TeamExistsAction(PreRunParseTokenMixin, actions.Action):

    def run(self, *args, **kwargs):
        exists = models.Team.objects.filter(
            pk=self.request.team_id,
            organization_id=self.parsed_token.organization_id,
        ).exists()
        if not exists:
            raise self.ActionFieldError('team_id', 'DOES_NOT_EXIST')


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


class AddMembers(TeamExistsAction):

    required_fields = ('team_id', 'members',)
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        super(AddMembers, self).run(*args, **kwargs)
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


class GetMembers(TeamExistsAction):

    required_fields = ('team_id',)
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        super(GetMembers, self).run(*args, **kwargs)
        members = models.TeamMember.objects.filter(
            organization_id=self.parsed_token.organization_id,
            team_id=self.request.team_id,
            role=self.request.role,
        )
        if not members:
            return

        members = self.get_paginated_objects(members)
        profile_ids = [str(member.profile_id) for member in members]
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


class UpdateMembers(TeamExistsAction):

    required_fields = ('team_id', 'members')
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        super(UpdateMembers, self).run(*args, **kwargs)
        _, permissions = get_permissions_for_team(
            team_id=self.request.team_id,
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        if not permissions.can_edit:
            raise self.PermissionDenied()

        update_members(
            team_id=self.request.team_id,
            organization_id=self.parsed_token.organization_id,
            members=self.request.members,
            token=self.token,
        )


class RemoveMembers(TeamExistsAction):

    required_fields = ('team_id', 'profile_ids')
    type_validators = {
        'team_id': [validators.is_uuid4],
        'profile_ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        super(RemoveMembers, self).run(*args, **kwargs)
        _, permissions = get_permissions_for_team(
            team_id=self.request.team_id,
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        if not permissions.can_edit:
            raise self.PermissionDenied()

        remove_members(
            team_id=self.request.team_id,
            organization_id=self.parsed_token.organization_id,
            profile_ids=self.request.profile_ids,
        )


class JoinTeam(TeamExistsAction):

    required_fields = ('team_id',)
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        super(JoinTeam, self).run(*args, **kwargs)
        member = team_containers.TeamMemberV1(profile_id=self.parsed_token.profile_id)
        add_members(
            [member],
            self.request.team_id,
            organization_id=self.parsed_token.organization_id,
        )


class LeaveTeam(TeamExistsAction):

    required_fields = ('team_id',)
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        super(LeaveTeam, self).run(*args, **kwargs)
        try:
            membership = models.TeamMember.objects.get(
                profile_id=self.parsed_token.profile_id,
                organization_id=self.parsed_token.organization_id,
                team_id=self.request.team_id,
            )
        except models.TeamMember.DoesNotExist:
            return

        if membership.role == team_containers.TeamMemberV1.COORDINATOR:
            if not models.TeamMember.objects.filter(
                organization_id=self.parsed_token.organization_id,
                team_id=self.request.team_id,
                role=team_containers.TeamMemberV1.COORDINATOR,
            ).count() > 1:
                raise self.ActionError(
                    'ONE_COORDINATOR_REQUIRED',
                    ('ONE_COORDINATOR_REQUIRED', 'at least one coordinator is required in a team'),
                )

        membership.delete()


class UpdateTeam(PreRunParseTokenMixin, actions.Action):

    required_fields = ('team',)

    def run(self, *args, **kwargs):
        try:
            team = models.Team.objects.get(
                id=self.request.team.id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.Team.DoesNotExist:
            raise self.ActionFieldError('team.id', 'DOES_NOT_EXIST')

        _, permissions = get_permissions_for_team(
            team_id=self.request.team.id,
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        if not permissions.can_edit:
            raise self.PermissionDenied()

        team = update_team(
            container=self.request.team,
            model=team,
            by_profile_id=self.parsed_token.profile_id,
            token=self.token,
            organization_id=self.parsed_token.organization_id,
        )
        team.to_protobuf(self.response.team)
