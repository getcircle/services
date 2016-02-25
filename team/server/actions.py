from common import utils
from django.db.models import Count
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
    get_permissions_for_teams,
    get_team,
    get_team_id_to_member_count,
    get_teams,
    remove_members,
    update_members,
    update_team,
)
from .. import models


def export_members_with_profiles(members, token, repeated_container):
    profile_ids = [str(member.profile_id) for member in members]
    profiles = service.control.get_object(
        service='profile',
        action='get_profiles',
        client_kwargs={'token': token},
        control={'paginator': {'page_size': len(profile_ids)}},
        return_object='profiles',
        ids=profile_ids,
        inflations={'disabled': True},
    )
    profile_id_to_profile = dict((p.id, p) for p in profiles)
    for member in members:
        container = repeated_container.add()
        profile = profile_id_to_profile.get(str(member.profile_id))
        # TODO remove redundant protobuf_to_dict
        if profile:
            profile = protobuf_to_dict(profile)

        member.to_protobuf(
            container,
            inflations={'only': ['profile']},
            profile=profile,
        )


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

        members = list(self.request.members)
        members.append(coordinator)
        add_members(members, team.id, organization_id=self.parsed_token.organization_id)

        permissions_dict = get_permissions_for_teams(
            team_ids=[team.id],
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        _, permissions = permissions_dict[str(team.id)]
        self.response.team.permissions.CopyFrom(permissions)


class AddMembers(TeamExistsAction):

    required_fields = ('team_id', 'members',)
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        super(AddMembers, self).run(*args, **kwargs)
        members = add_members(
            self.request.members,
            self.request.team_id,
            organization_id=self.parsed_token.organization_id,
        )
        export_members_with_profiles(
            members=members,
            token=self.token,
            repeated_container=self.response.members,
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
        permissions_dict = get_permissions_for_teams(
            team_ids=[team.id],
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        member, permissions = permissions_dict[str(team.id)]
        if member:
            member.to_protobuf(self.response.member)
        self.response.team.permissions.CopyFrom(permissions)


class GetTeams(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        # we don't support get_teams contact_methods yet
        self.request.inflations.exclude.append('contact_methods')

        teams = get_teams(
            self.parsed_token.organization_id,
            ids=self.request.ids,
        )
        teams = self.get_paginated_objects(teams)
        if not teams:
            return

        team_id_to_member_count_dict = {}
        if utils.should_inflate_field('total_members', self.request.inflations):
            team_id_to_member_count_dict = get_team_id_to_member_count(teams)

        team_id_to_permissions_dict = {}
        if utils.should_inflate_field('permissions', self.request.inflations):
            team_id_to_permissions_dict = get_permissions_for_teams(
                team_ids=[str(t.id) for t in teams],
                profile_id=self.parsed_token.profile_id,
                organization_id=self.parsed_token.organization_id,
                token=self.token,
            )

        for team in teams:
            container = self.response.teams.add()
            permissions = team_id_to_permissions_dict.get(str(team.id), (None, None))[1]
            if permissions:
                # XXX redundant protobuf_to_dict
                permissions = protobuf_to_dict(permissions)

            team.to_protobuf(
                container,
                inflations=self.request.inflations,
                fields=self.request.fields,
                token=self.token,
                total_members=team_id_to_member_count_dict.get(str(team.id)),
                permissions=permissions,
            )


class GetMembers(TeamExistsAction):

    type_validators = {
        'profile_id': [validators.is_uuid4],
        'team_id': [validators.is_uuid4],
    }

    def validate(self, *args, **kwargs):
        super(GetMembers, self).validate(*args, **kwargs)
        if not self.is_error():
            if not self.request.team_id and not self.request.profile_id:
                raise self.ActionFieldError('team_id', 'MISSING')

    def _get_members_with_team_id(self):
        exists = models.Team.objects.filter(
            pk=self.request.team_id,
            organization_id=self.parsed_token.organization_id,
        ).exists()
        if not exists:
            raise self.ActionFieldError('team_id', 'DOES_NOT_EXIST')

        return models.TeamMember.objects.filter(
            organization_id=self.parsed_token.organization_id,
            team_id=self.request.team_id,
            role=self.request.role,
        )

    def _get_members_with_profile_id(self):
        return models.TeamMember.objects.filter(
            organization_id=self.parsed_token.organization_id,
            profile_id=self.request.profile_id,
        ).order_by('-role')

    def run(self, *args, **kwargs):
        if self.request.team_id:
            members = self._get_members_with_team_id()
        else:
            members = self._get_members_with_profile_id()

        # XXX protect against inflating all teams improperly
        member_fields = utils.fields_for_repeated_items('members', self.request.fields)
        member_inflations = utils.inflations_for_repeated_items('members', self.request.inflations)

        if self.request.profile_id and utils.should_inflate_field('team', member_inflations):
            members = members.select_related('team')

        members = self.get_paginated_objects(members)
        if not members:
            return

        profile_id_to_profile = {}
        if utils.should_inflate_field('profile', member_inflations):
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

        team_id_to_team_dict = {}
        if self.request.profile_id and utils.should_inflate_field('team', member_inflations):
            team_inflations = utils.inflations_for_item('team', member_inflations)
            team_fields = utils.fields_for_item('team', member_fields)

            team_id_to_count_dict = {}
            if utils.should_inflate_field('total_members', team_inflations):
                counts = models.TeamMember.objects.filter(
                    team_id__in=[m.team_id for m in members],
                    organization_id=self.parsed_token.organization_id,
                ).values('team_id').annotate(total_members=Count('id'))
                team_id_to_count_dict = dict(
                    (str(v['team_id']), v['total_members']) for v in counts
                )

            # TODO reorder these members based on member count
            for member in members:
                # XXX protect against querying for contact methods for each team
                container = member.team.to_protobuf(
                    inflations=team_inflations,
                    fields=team_fields,
                    total_members=team_id_to_count_dict.get(str(member.team.id), 0),
                )
                team_id_to_team_dict[container.id] = container

        for member in members:
            container = self.response.members.add()
            # XXX remove these redundant protobuf_to_dict calls
            profile = profile_id_to_profile.get(str(member.profile_id))
            if profile:
                profile = protobuf_to_dict(profile)

            team = team_id_to_team_dict.get(str(member.team_id))
            if team:
                team = protobuf_to_dict(team)

            member.to_protobuf(
                container,
                profile=profile,
                fields=member_fields,
                inflations=member_inflations,
                team=team,
            )


class UpdateMembers(TeamExistsAction):

    required_fields = ('team_id', 'members')
    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        super(UpdateMembers, self).run(*args, **kwargs)
        permissions_dict = get_permissions_for_teams(
            team_ids=[self.request.team_id],
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        _, permissions = permissions_dict[self.request.team_id]
        if not permissions.can_edit:
            raise self.PermissionDenied()

        members = update_members(
            team_id=self.request.team_id,
            organization_id=self.parsed_token.organization_id,
            members=self.request.members,
            token=self.token,
        )
        export_members_with_profiles(
            members=members,
            token=self.token,
            repeated_container=self.response.members,
        )


class RemoveMembers(TeamExistsAction):

    required_fields = ('team_id', 'profile_ids')
    type_validators = {
        'team_id': [validators.is_uuid4],
        'profile_ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        super(RemoveMembers, self).run(*args, **kwargs)
        permissions_dict = get_permissions_for_teams(
            team_ids=[self.request.team_id],
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        _, permissions = permissions_dict[self.request.team_id]
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
        member = add_members(
            [member],
            self.request.team_id,
            organization_id=self.parsed_token.organization_id,
        )[0]
        member.to_protobuf(self.response.member)


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

    def validate(self, *args, **kwargs):
        super(UpdateTeam, self).validate(*args, **kwargs)
        if not self.is_error():
            for index, method in enumerate(self.request.team.contact_methods):
                if not method.value:
                    raise self.ActionFieldError('contact_methods[%d].value' % (index,), 'MISSING')

    def run(self, *args, **kwargs):
        try:
            team = models.Team.objects.get(
                id=self.request.team.id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.Team.DoesNotExist:
            raise self.ActionFieldError('team.id', 'DOES_NOT_EXIST')

        permissions_dict = get_permissions_for_teams(
            team_ids=[self.request.team.id],
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            token=self.token,
        )
        _, permissions = permissions_dict[self.request.team.id]
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
        self.response.team.permissions.CopyFrom(permissions)
