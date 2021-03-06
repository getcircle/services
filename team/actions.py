from bulk_update.helper import bulk_update
import django.db
from django.db.models import Count

from protobufs.services.common import containers_pb2 as common_containers
from protobufs.services.history import containers_pb2 as history_containers
from protobufs.services.team import containers_pb2 as team_containers
import service.control

from services.history import (
    action_container_for_create,
    action_container_for_update,
)

from . import models


def get_permissions_for_teams(team_ids, profile_id, organization_id, token):
    """Return permissions for the given user for the requested teams.

    Args:
        team_ids (List[str]): list of team ids
        profile_id (str): id of the profile we're checking permissions against
        organization_id (str): id of the organization
        token (str): service token

    Returns:
        dictionary with <team_id>: (models.TeamMember,
        services.common.containers.PermissionsV1) tuple with team member object
        if the user is a member of the team and the permissions object.

    """
    memberships = models.TeamMember.objects.filter(
        team_id__in=team_ids,
        profile_id=profile_id,
        organization_id=organization_id,
    )
    team_id_to_membership = dict((str(m.team_id), m) for m in memberships)
    profile = service.control.get_object(
        service='profile',
        action='get_profile',
        client_kwargs={'token': token},
        return_object='profile',
        profile_id=profile_id,
        inflations={'disabled': True},
        fields={'only': ['is_admin']},
    )

    team_id_to_permissions = {}
    for team_id in team_ids:
        permissions = common_containers.PermissionsV1()
        membership = team_id_to_membership.get(str(team_id))
        if (
            membership and membership.role == team_containers.TeamMemberV1.COORDINATOR or
            profile.is_admin
        ):
            permissions.can_edit = True
            permissions.can_add = True
            permissions.can_delete = True
        elif membership:
            permissions.can_add = True
        team_id_to_permissions[str(team_id)] = (membership, permissions)
    return team_id_to_permissions


def create_team(container, by_profile_id, token, organization_id, **overrides):
    """Create a team.

    Create a team and record who created the team within the history service.

    Args:
        container (protobufs.services.team.containers.TeamV1): protobuf container to
            convert into a model
        by_profile_id (uuid): profile id of user creating the team
        token (str): service token
        organization_id (uuid): organization id

    Returns:
        team.models.Team model

    """
    if container.description.value:
        container.description.by_profile_id = by_profile_id

    team = models.Team.objects.from_protobuf(
        container,
        organization_id=organization_id,
        **overrides
    )
    service.control.call(
        service='history',
        action='record_action',
        client_kwargs={'token': token},
        action_kwargs={'action': action_container_for_create(team)},
    )
    return team


def update_team(container, model, by_profile_id, token, organization_id):
    """Update a team.

    Args:
        container (protobufs.services.team.containers.TeamV1): protobuf container
        model (team.models.Team): the team model we're updating
        by_profile_id (uuid): profile id of the user updating the team
        token: (str): service token
        organization_id (uuid): organization id

    Returns:
        team.models.Team model updated from the protobuf

    """
    if container.description.value != (model.description and model.description.value or ''):
        container.description.by_profile_id = by_profile_id

    model.update_from_protobuf(container)
    model.save()
    return model


def add_members(containers, team_id, organization_id, **overrides):
    """Add members to a team.

    Args:
        containers (protobufs.services.team.containers.TeamMemberV1): team
            members to add to the team
        team_id (str): id of the team to add the members to

    """
    ids = set()
    objects = []
    for container in containers:
        if container.profile_id not in ids:
            obj = models.TeamMember.objects.from_protobuf(
                container,
                commit=False,
                team_id=team_id,
                organization_id=organization_id,
                **overrides
            )
            objects.append(obj)
            ids.add(container.profile_id)
    return models.TeamMember.objects.bulk_create(objects)


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


def get_teams(organization_id, ids=None):
    """Return the teams for the organization.

    Args:
        organization_id (str): organization id

    Returns:
        models.Team queryset

    """
    parameters = {'organization_id': organization_id}
    if ids:
        parameters['id__in'] = ids
    return models.Team.objects.filter(**parameters)


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
    return existing_members


def remove_members(team_id, organization_id, profile_ids):
    """Remove the given profile_ids from the team.

    Args:
        team_id (uuid): id for the team
        organization_id (uuid): id for the organization
        profile_ids (repeated uuid): profile ids to remove from the team

    """
    members = models.TeamMember.objects.filter(
        team_id=team_id,
        organization_id=organization_id,
        profile_id__in=profile_ids,
    )
    if members:
        with django.db.transaction.atomic():
            members.delete()
            coordinators = models.TeamMember.objects.filter(
                team_id=team_id,
                organization_id=organization_id,
                role=team_containers.TeamMemberV1.COORDINATOR,
            )
            assert len(coordinators) > 0


def update_contact_methods(contact_methods, team):
    """Update the contact methods for a team.

    Args:
        contact_methods (repeated
            protobufs.services.team.containers.ContactMethodV1): contact methods
        team (team.models.Team): team model we're updating

    Returns:
        repeated protobufs.services.team.containers.ContactMethodV1

    """
    with django.db.transaction.atomic():
        existing_methods = team.contact_methods.filter(organization_id=team.organization_id)
        existing_methods_dict = dict((str(method.id), method) for method in existing_methods)
        existing_ids = set(existing_methods_dict.keys())
        new_ids = set(method.id for method in contact_methods if method.id)
        to_delete = existing_ids - new_ids

        to_create = []
        to_update = []
        for container in contact_methods:
            if not container.value:
                continue

            if container.id:
                contact_method = existing_methods_dict[container.id]
                contact_method.update_from_protobuf(container)
                to_update.append(contact_method)
            else:
                contact_method = models.ContactMethod.objects.from_protobuf(
                    container,
                    team_id=team.id,
                    organization_id=team.organization_id,
                    commit=False,
                )
                to_create.append(contact_method)

        if to_create:
            models.ContactMethod.objects.bulk_create(to_create)

        if to_update:
            bulk_update(to_update)

        if to_delete:
            team.contact_methods.filter(
                id__in=to_delete,
                organization_id=team.organization_id,
            ).delete()


def get_team_id_to_member_count(teams):
    counts = models.TeamMember.objects.filter(
        organization_id=teams[0].organization_id,
        team_id__in=[t.id for t in teams],
    ).values('team_id').annotate(total_members=Count('id'))
    return dict((str(count['team_id']), count['total_members']) for count in counts)
