from bulk_update.helper import bulk_update
from django.db.models import Max
from protobufs.services.common import containers_pb2 as common_containers
from protobufs.services.post import containers_pb2 as post_containers
import service.control
from service.actions import Action

from . import models


def get_collection_permissions(collection, by_profile_id, token):
    """Return the requesting users permissions for the collection.

    Args:
        collection (post.models.Collection): collection we're checking against
        by_profile_id (str): profile id making the request
        token (str): service token

    Returns:
        servicse.common.containers.PermissionsV1

    """
    permissions = common_containers.PermissionsV1()
    full_permissions = False

    if collection.owner_type == post_containers.CollectionV1.TEAM:
        team_permissions = get_team_permissions(str(collection.owner_id), token)
        if team_permissions.can_edit:
            full_permissions = True
    elif collection.owner_type == post_containers.CollectionV1.PROFILE:
        if by_profile_id == str(collection.owner_id):
            full_permissions = True
        else:
            profile = service.control.get_object(
                service='profile',
                action='get_profile',
                return_object='profile',
                client_kwargs={'token': token},
                fields={'only': ['is_admin']},
                profile_id=by_profile_id,
            )
            if profile.is_admin:
                full_permissions = True

    if full_permissions:
        permissions.can_edit = True
        permissions.can_add = True
        permissions.can_delete = True
    return permissions


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


def check_collection_permission(permission, collection_id, organization_id, by_profile_id, token):
    """Raise Action.PermissionDenied if the profile doesn't have the specified permission.

    Args:
        permission (str): one of ('can_add', 'can_delete', 'can_edit') the user
            must have
        collection_id (str): id of the collection
        organization_id (str): id of the organization
        by_profile_id (str): id of the proilfe
        token (str): service token

    Raises:
        post.models.Collection.DoesNotExist if the collection does not exist
        Action.PermissionDenied if the user doesn't have permission to delete
            the collection

    Returns:
        post.models.Collection if the user has the correct permission

    """
    collection = models.Collection.objects.get(
        pk=collection_id,
        organization_id=organization_id,
    )
    permissions = get_collection_permissions(
        collection=collection,
        by_profile_id=by_profile_id,
        token=token,
    )
    if not permissions.can_delete:
        raise Action.PermissionDenied()

    return collection


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
    collection = check_collection_permission(
        permission='can_delete',
        collection_id=collection_id,
        organization_id=organization_id,
        by_profile_id=by_profile_id,
        token=token,
    )

    collection.delete()


def reorder_collection(collection_id, organization_id, by_profile_id, position_diffs, token):
    """Reorder items within a collection.

    Args:
        collection_id (str): id of the collection
        organization_id (str): id of the organization
        by_profile_id (str): id of the profile requesting the reorder
        position_diffs (List[services.post.actions.reorder_collection.PositionDiffV1]):
            posiiton diff of items that have been reordered in the collection
        token (str): service token

    Raises:
        post.models.Collection.DoesNotExist if the collection does not exist
        Action.PermissionDenied if the user doesn't have permission to edit
            the collection

    """
    check_collection_permission(
        permission='can_edit',
        collection_id=collection_id,
        organization_id=organization_id,
        by_profile_id=by_profile_id,
        token=token,
    )

    min_position = min([position for diff in position_diffs
                        for position in (diff.current_position, diff.new_position)])

    items = list(models.CollectionItem.objects.filter(
        collection_id=collection_id,
        organization_id=organization_id,
        position__gte=min_position,
    ).order_by('position'))

    for diff in position_diffs:
        # noramlize the positions relative to the slice we fetched from the db
        diff.current_position = diff.current_position - min_position
        diff.new_position = diff.new_position - min_position
        item = items.pop(diff.current_position)
        items.insert(diff.new_position, item)

    for index, item in enumerate(items):
        item.position = index + min_position

    bulk_update(items, update_fields=['position', 'changed'])


def add_to_collection(collection_id, source, source_id, organization_id, by_profile_id, token):
    """Add an item to a collection.

    Args:
        collection_id (str): id of the collection
        source (services.post.containers.CollectionItemV1.SourceV1): source of
            the item being added
        source_id (str): id of the item within the source
        organization_id (str): id of the organization
        by_profile_id (str): id of the profile requesting the change
        token (str): service token

    Returns:
        post.models.CollectionItem

    Raises:
        post.models.Collection.DoesNotExist if the collection does not exist
        Action.PermissionDenied if the user doesn't have permission to edit
            the collection

    """
    check_collection_permission(
        permission='can_edit',
        collection_id=collection_id,
        organization_id=organization_id,
        by_profile_id=by_profile_id,
        token=token,
    )

    position = 0
    max_position = models.CollectionItem.objects.filter(
        organization_id=organization_id,
        collection_id=collection_id,
    ).aggregate(Max('position'))['position__max']
    if max_position is not None:
        position = max_position

    return models.CollectionItem.objects.create(
        organization_id=organization_id,
        collection_id=collection_id,
        source=source,
        source_id=source_id,
        by_profile_id=by_profile_id,
        position=position,
    )


def remove_from_collection(
        collection_id,
        collection_item_id,
        organization_id,
        by_profile_id,
        token,
    ):
    """Remove an item from a collection.

    Args:
        collection_id (str): id of the collection
        collection_item_id (str): id of the item in the collection
        organization_id (str): id of the organization
        by_profile_id (str): id of the profile requesting the change
        token (str): service token

    Raises:
        post.models.Collection.DoesNotExist if the collection does not exist
        Action.PermissionDenied if the user doesn't have permission to edit
            the collection

    """
    check_collection_permission(
        permission='can_edit',
        collection_id=collection_id,
        organization_id=organization_id,
        by_profile_id=by_profile_id,
        token=token,
    )

    try:
        item = models.CollectionItem.objects.get(
            organization_id=organization_id,
            id=collection_item_id,
            collection_id=collection_id,
        )
    except models.CollectionItem.DoesNotExist:
        return
    else:
        item.delete()


def update_collection(container, organization_id, by_profile_id, token):
    """Update a collection.

    Args:
        container (services.post.containers.CollectionV1): container we're updating off of
        organization_id (str): id of the organization
        by_profile_id (str): id of the profile requesting the change
        token (str): service token

    Returns:
        post.models.Collection

    Raises:
        post.models.Collection.DoesNotExist if the collection does not exist
        Action.PermissionDenied if the user doesn't have permission to edit
            the collection

    """
    collection = check_collection_permission(
        permission='can_edit',
        collection_id=container.id,
        organization_id=organization_id,
        by_profile_id=by_profile_id,
        token=token,
    )
    collection.update_from_protobuf(
        container,
        commit=True,
        ignore_fields=['owner_type', 'owner_id'],
    )
    return collection
