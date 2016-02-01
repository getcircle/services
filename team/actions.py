import service.control

from services.history import action_container_for_create

from . import models


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
