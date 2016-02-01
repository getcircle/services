from protobufs.services.common import containers_pb2 as common_containers
from protobufs.services.history import containers_pb2 as history_containers
from protobufs.services.team import containers_pb2 as team_containers
import service.control

from services.history import (
    action_container_for_create,
    action_container_for_update,
)

from . import models


def get_permissions_for_team(team_id, profile_id, organization_id, token):
    """Return permissions for the given user for the requested team.

    Args:
        team_id (uuid): team id
        profile_id (uuid): profile id of the user we want to return permissions for
        organization_id (uuid): organization id
        token (services.token): token to forward along to service calls

    Returns:
        (bool, protobufs.services.common.containers.PermissionsV1) tuple with a
        boolean for if the user is a member of the team and the permissions
        object

    """
    try:
        membership = models.TeamMember.objects.get(
            team_id=team_id,
            profile_id=profile_id,
            organization_id=organization_id,
        )
    except models.TeamMember.DoesNotExist:
        membership = None

    permissions = common_containers.PermissionsV1()

    profile = service.control.get_object(
        service='profile',
        action='get_profile',
        client_kwargs={'token': token},
        return_object='profile',
        profile_id=profile_id,
        inflations={'disabled': True},
        fields={'only': ['is_admin']},
    )

    if (
        membership and membership.role == team_containers.TeamMemberV1.COORDINATOR or
        profile.is_admin
    ):
        permissions.can_edit = True
        permissions.can_add = True
        permissions.can_delete = True
    elif membership:
        permissions.can_add = True
    return bool(membership), permissions


def create_team(container, by_profile_id, token, **overrides):
    """Create a team.

    Create a team and record who created the team within the history service.

    Args:
        container (protobufs.services.team.containers.TeamV1): protobuf container to
            convert into a model
        token (str): service token

    Returns:
        team.models.Team model

    """
    if container.description.value:
        container.description.by_profile_id = by_profile_id

    team = models.Team.objects.from_protobuf(container, **overrides)
    service.control.call(
        service='history',
        action='record_action',
        client_kwargs={'token': token},
        action_kwargs={'action': action_container_for_create(team)},
    )
    return team


def add_members(containers, team_id, **overrides):
    """Add members to a team.

    Args:
        containers (protobufs.services.team.containers.TeamMemberV1): team
            members to add to the team
        team_id (str): id of the team to add the members to

    """
    objects = [models.TeamMember.objects.from_protobuf(
        container,
        commit=False,
        team_id=team_id,
        **overrides
    ) for container in containers]
    models.TeamMember.objects.bulk_create(objects)


def get_team(team_id, organization_id):
    """Return a team.

    Args:
        team_id (uuid4): team id
        organization_id (uuid4): organization id

    Returns:
        models.Team object

    Raises:
        models.Team.DoesNotExist: if the object doesn't exist

    """
    return models.Team.objects.get(pk=team_id, organization_id=organization_id)


def update_members(team_id, organization_id, members, token):
    """Update members to their new roles.

    This method updates members to the role provided, tracking who made the
    change as well. If the member role did not change or the member does not
    exist, we do nothing.

    Args:
        team_id (uuid4): team id
        organization_id (uuid4): organization id
        members (repeated protobufs.services.team.containers.TeamMemberV1):
            members with new roles
        token (services.token): token

    """
    profile_id_to_new_member = dict((m.profile_id, m) for m in members)
    existing_members = models.TeamMember.objects.filter(
        team_id=team_id,
        organization_id=organization_id,
        profile_id__in=profile_id_to_new_member.keys(),
    )
    for member in existing_members:
        new_member = profile_id_to_new_member[str(member.profile_id)]
        if new_member.role != member.role:
            action = action_container_for_update(
                instance=member,
                field_name='role',
                new_value=new_member.role,
                action_type=history_containers.UPDATE_TEAM_MEMBER_ROLE,
            )
            service.control.call(
                service='history',
                action='record_action',
                client_kwargs={'token': token},
                action_kwargs={'action': action},
            )
            member.role = new_member.role
            member.save()
