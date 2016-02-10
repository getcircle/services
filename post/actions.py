from protobufs.services.post import containers_pb2 as post_containers
import service.control
from service.actions import Action

from . import models


def get_team_permissions(team_id, token):
    """Return the permissions object for the given team.

    Permissions will be based on the user info stored in the token.

    Args:
        team_id (str): id of the team
        token (str): service token

    Returns:
        services.common.containers.PermissionsV1

    """
    team = service.control.get_object(
        service='team',
        action='get_team',
        return_object='team',
        client_kwargs={'token': token},
        fields={'only': ['permissions']},
        team_id=team_id,
    )
    return team.permissions


def create_collection(container, organization_id, by_profile_id, token):
    """Create a collection.

    Args:
        container (protobufs.services.post.containers.CollectionV1): protobuf
            container to convert into a model
        organization_id (str): organization id
        by_profile_id (str): profile id making the request
        token (str): service token

    Returns:

        post.models.Collection

    """
    profile_id = None
    if container.owner_type == post_containers.CollectionV1.TEAM:
        profile_id = by_profile_id
        permissions = get_team_permissions(container.owner_id, token)
        if not permissions.can_edit:
            raise Action.PermissionDenied()

    elif container.owner_type == post_containers.CollectionV1.PROFILE:
        container.owner_id = by_profile_id

    return models.Collection.objects.from_protobuf(
        container,
        organization_id=organization_id,
        by_profile_id=profile_id,
    )


def delete_collection(collection_id, organization_id, by_profile_id, token):
    """Delete a collection

    Args:
        collection_id (str): id of the collection to delete
        organization_id (str): organization id
        by_profile_id (str): profile making the request
        token (str): service token

    Raises:

        post.models.Collection.DoesNotExist if the collection does not exist
        Action.PermissionDenied if the user doesn't have permission to delete
            the collection

    """
    collection = models.Collection.objects.get(
        pk=collection_id,
        organization_id=organization_id,
    )
    if collection.owner_type == post_containers.CollectionV1.TEAM:
        permissions = get_team_permissions(str(collection.owner_id), token)
        if not permissions.can_delete:
            raise Action.PermissionDenied()
    elif collection.owner_type == post_containers.CollectionV1.PROFILE:
        if by_profile_id != str(collection.owner_id):
            profile = service.control.get_object(
                service='profile',
                action='get_profile',
                return_object='profile',
                client_kwargs={'token': token},
                fields={'only': ['is_admin']},
                profile_id=by_profile_id,
            )
            if not profile.is_admin:
                raise Action.PermissionDenied()

    collection.delete()
