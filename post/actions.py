import logging

from bulk_update.helper import bulk_update
from common import utils
from django.db.models import (
    Count,
    Max,
    Q,
)
from protobuf_to_dict import protobuf_to_dict
from protobufs.services.common import containers_pb2 as common_containers
from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.team import containers_pb2 as team_containers
import service.control
from service.actions import Action

from . import models

logger = logging.getLogger(__name__)


def collection_exists(collection_id, organization_id):
    """Determine whether or not the collection exists.

    Args:
        collection_id (str): id of the collection
        organization_id (str): id of the organization

    Returns:
        Boolean for whether or not the collection exists

    """
    return models.Collection.objects.filter(
        pk=collection_id,
        organization_id=organization_id,
    ).exists()


def get_permissions_for_collections(collections, by_profile_id, token):

    def get_permissions(full=False):
        return common_containers.PermissionsV1(
            can_edit=full,
            can_add=full,
            can_delete=full,
        )

    def get_profile():
        return service.control.get_object(
            service='profile',
            action='get_profile',
            return_object='profile',
            client_kwargs={'token': token},
            fields={'only': ['is_admin']},
            profile_id=by_profile_id,
        )

    team_ids = set([
        str(collection.owner_id) for collection in collections
        if collection.owner_type == post_containers.CollectionV1.TEAM
    ])

    team_id_to_team_dict = {}
    if team_ids:
        teams = service.control.get_object(
            service='team',
            action='get_teams',
            return_object='teams',
            client_kwargs={'token': token},
            control={'paginator': {'page_size': len(team_ids)}},
            fields={'only': ['id', 'permissions']},
            ids=list(team_ids),
        )
        team_id_to_team_dict = dict((team.id, team) for team in teams)

    profile = None

    collection_id_to_permissions = {}
    for collection in collections:
        full_permissions = False
        if collection.owner_type == post_containers.CollectionV1.TEAM:
            team = team_id_to_team_dict.get(str(collection.owner_id))
            if team and team.permissions.can_edit:
                full_permissions = True
        elif (
            collection.owner_type == post_containers.CollectionV1.PROFILE and
            str(collection.owner_id) == by_profile_id
        ):
            full_permissions = True

        if not full_permissions:
            if not profile:
                profile = get_profile()
            if profile.is_admin:
                full_permissions = True
        collection_id_to_permissions[str(collection.id)] = get_permissions(full_permissions)
    return collection_id_to_permissions


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
        inflations={'disabled': True},
        fields={'only': ['permissions']},
        team_id=team_id,
    )
    return team.permissions


def get_editable_collections(by_profile_id, organization_id, token):
    profile = service.control.get_object(
        service='profile',
        action='get_profile',
        return_object='profile',
        client_kwargs={'token': token},
        fields={'only': ['is_admin']},
        profile_id=by_profile_id,
    )

    queryset = models.Collection.objects.filter(organization_id=organization_id)
    if profile.is_admin:
        return queryset.filter(
            (
                Q(owner_type=post_containers.CollectionV1.PROFILE) &
                Q(owner_id=by_profile_id)
            ) |
            Q(owner_type=post_containers.CollectionV1.TEAM)
        )
    else:
        # get the teams they're a coordinator of
        members = service.control.get_object(
            service='team',
            action='get_members',
            return_object='members',
            client_kwargs={'token': token},
            # TODO come up with a better way to specify all results
            control={'paginator': {'page_size': 1000}},
            inflations={'disabled': True},
            fields={'only': ['[]members.team_id']},
            profile_id=by_profile_id,
            role=team_containers.TeamMemberV1.COORDINATOR,
            has_role=True,
        )
        team_ids = [m.team_id for m in members]
        profile_collections = queryset.filter(
            Q(owner_type=post_containers.CollectionV1.PROFILE) & Q(owner_id=by_profile_id)
        )
        if team_ids:
            team_collections = queryset.filter(
                Q(owner_type=post_containers.CollectionV1.TEAM) & Q(owner_id__in=team_ids)
            )
            queryset = profile_collections | team_collections
        else:
            queryset = profile_collections
    return queryset


def get_collections_with_permissions(
        permission,
        collection_ids,
        organization_id,
        by_profile_id,
        token,
    ):
    collections = models.Collection.objects.filter(
        pk__in=collection_ids,
        organization_id=organization_id,
    )
    collection_to_permissions = {}
    if collections:
        collection_to_permissions = get_permissions_for_collections(
            collections=collections,
            by_profile_id=by_profile_id,
            token=token,
        )

    collections_with_permissions = []
    for collection in collections:
        permissions = collection_to_permissions[str(collection.id)]
        if getattr(permissions, permission):
            collections_with_permissions.append(collection)
    return collections_with_permissions


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
    collection_to_permissions = get_permissions_for_collections(
        collections=[collection],
        by_profile_id=by_profile_id,
        token=token,
    )
    permissions = collection_to_permissions[str(collection.id)]
    if not getattr(permissions, permission):
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


def get_collection(
        organization_id,
        collection_id=None,
        is_default=False,
        owner_type=None,
        owner_id=None,
    ):
    """Get a specific collection.

    Args:
        organization_id (str): id of the organization
        collection_id (Optional[str]): id of the collection
        is_default (Optional[bool]): whether or not we're fetching the default collection
        owner_type (Optional[services.post.containers.CollectionV1.OwnerTypeV1]): owner type
            of the default collection, required when fetching the default
            collection
        owner_id (Optional[str]): owner id of the default collection, required
            when fetching the default collection

    Returns:
        post.models.Collection

    Raises:
        post.models.Collection.DoesNotExist if the collection does not exist

    """

    if is_default and not all([owner_type and owner_id]):
        raise TypeError('Must provide `owner_type` and `owner_id` with `is_default`')

    lookups = ['collection_id', 'is_default']
    if not any([lookups]):
        raise TypeError('Must provide one of %s' % (lookups,))

    parameters = {'organization_id': organization_id}
    if collection_id:
        parameters['pk'] = collection_id
    else:
        # XXX test owner_type and owner_id being None
        parameters['is_default'] = True
        parameters['owner_type'] = owner_type
        parameters['owner_id'] = owner_id

    return models.Collection.objects.get(**parameters)


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


def add_to_collections(item, collections, organization_id, by_profile_id, token):
    """Add an item to a collection.

    Args:
        item (services.post.containers.CollectionItemV1): item to add to collections
        collections (List[services.post.containers.CollectionV1]): list of
            collections to add the item to
        organization_id (str): id of the organization
        by_profile_id (str): id of the profile requesting the change
        token (str): service token

    Returns:
        List[post.models.CollectionItem]

    """

    collections = get_collections_with_permissions(
        permission='can_add',
        collection_ids=[c.id for c in collections],
        organization_id=organization_id,
        by_profile_id=by_profile_id,
        token=token,
    )

    positions = models.CollectionItem.objects.filter(
        organization_id=organization_id,
        collection_id__in=[c.id for c in collections],
    ).values('collection_id').annotate(position=Max('position'))
    collection_to_position = dict((str(p['collection_id']), p['position']) for p in positions)

    items = []
    for collection in collections:
        position = collection_to_position.get(str(collection.id), None)
        if position is None:
            position = 0
        else:
            position += 1
        item = models.CollectionItem(
            organization_id=organization_id,
            collection_id=collection.id,
            source=item.source,
            source_id=item.source_id,
            by_profile_id=by_profile_id,
            position=position,
        )
        items.append(item)

    if items:
        items = models.CollectionItem.objects.bulk_create(items)
    return items


def remove_from_collections(
        item,
        collections,
        organization_id,
        by_profile_id,
        token,
    ):
    """Remove an item from collections.

    Args:
        item (services.post.containers.CollectionItemV1): collection item to remove
        collections (List[services.post.containers.CollectionV1]): list of
            collections to remove the item from
        organization_id (str): id of the organization
        by_profile_id (str): id of the profile requesting the change
        token (str): service token

    """
    collections = get_collections_with_permissions(
        permission='can_add',
        collection_ids=[c.id for c in collections],
        organization_id=organization_id,
        by_profile_id=by_profile_id,
        token=token,
    )
    if collections:
        items = models.CollectionItem.objects.filter(
            organization_id=organization_id,
            source_id=item.source_id,
            source=item.source,
            collection_id__in=[c.id for c in collections],
        )
        try:
            assert len(items) <= len(collections)
        except AssertionError:
            logger.error(
                'Attempting to remove more items than originally specified: %d vs. %d',
                len(items),
                len(collections),
            )
            raise
        else:
            items.delete()


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


def get_collections(
        organization_id,
        by_profile_id,
        token,
        owner_type=None,
        owner_id=None,
        source=None,
        source_id=None,
        is_default=False,
        ids=None,
        profile_id=None,
        permissions=None,
    ):
    """Return collections for the owner or source item.

    Args:
        organization_id (str): organization id
        by_profile_id (str): profile id fetching the collections
        token (str): token of the user fetching collections
        owner_type (Optional[services.post.containers.CollectionV1.OwnerTypeV1]): type of
            owner (relevant when owner_id is specified)
        owner_id (Optional[str]): id of the owner, used with owner_type to lookup Team or
            Profile collections
        source (Optional[services.post.containers.CollectionItemV1.SourceV1]):
            source of the item (relevant when source_id is specified)
        source_id (Optional[str]): id of the item we want to return the
            collections it belongs to, used with `source`
        is_default (Optional[bool]): whether or not we want to return just the
            default collection
        ids (Optional[List[str]]): specific collection ids to retrieve
        profile_id (Optional[str]): id of the profile we want to return
            collections for. This is used when we want to return collections a
            profile has access to edit
        permissions (Optional[services.common.containers.PermissionsV1]):
            permissions object. this is used if we want to return all
            collections for an item that the user has access to

    Returns:
        post.models.Collection queryset

    """
    parameters = {'organization_id': organization_id}
    if ids:
        parameters['id__in'] = ids

    if owner_id:
        collections = models.Collection.objects.filter(
            owner_id=owner_id,
            owner_type=owner_type,
            **parameters
        )
        # is_default is a NullBooleanField, we only store a value if
        # `is_default` is True
        if is_default:
            collections = collections.filter(is_default=is_default)
        else:
            collections = collections.filter(is_default=None)
    elif source_id:
        items = models.CollectionItem.objects.filter(
            source=source,
            source_id=source_id,
            **parameters
        )
        collections = [i.collection for i in items]
        if permissions.can_add:
            collections = get_collections_with_permissions(
                collection_ids=[i.collection_id for i in items],
                permission='can_add',
                organization_id=organization_id,
                by_profile_id=by_profile_id,
                token=token,
            )
    elif profile_id:
        collections = get_editable_collections(
            organization_id=organization_id,
            by_profile_id=by_profile_id,
            token=token,
        )
    else:
        collections = models.Collection.objects.filter(**parameters)
    return collections


def get_total_items_for_collections(collection_ids, organization_id):
    """Get the total items for the collections.

    Args:
        collections (List[str]): list of collection ids
        organization_id (str): id of the organization

    Returns:
        dictionary with <str(collection.id)>: <total items>

    """
    item_counts = models.CollectionItem.objects.filter(
        organization_id=organization_id,
        collection_id__in=collection_ids,
    ).values('collection').annotate(total_items=Count('id'))
    return dict((str(d['collection']), d['total_items']) for d in item_counts)


def get_posts_with_fields(ids, organization_id, fields):
    """Get posts but only include or defer fields based on specified fields object.

    Args:
        ids (List[str]): list of post ids
        organization_id (str): id of the organization
        fields (services.common.containers.FieldsV1): fields being requested

    Returns:
        post.models.Post queryset

    """
    posts = models.Post.objects.filter(
        organization_id=organization_id,
        id__in=ids,
    )
    if fields.only:
        posts = posts.only(*fields.only)

    if fields.exclude:
        posts = posts.defer(*fields.exclude)
    return posts


def get_collection_items(collection_id, organization_id):
    """Return the items for the given collection.

    Args:
        collection_id (str): id of the collection
        organization_id (str): id of the organization

    Returns;
        post.models.CollectionItem queryset

    """
    # XXX come back to this query
    return models.CollectionItem.objects.filter(
        collection_id=collection_id,
        organization_id=organization_id,
    ).order_by('position').exclude(
        source_id__in=models.Post.objects.exclude(
            state=post_containers.LISTED,
        ).extra(select={'source_id': 'id::varchar'}).values_list('source_id', flat=True),
    )


def inflate_items_source(items, organization_id, inflations, fields, token=None):
    """Given a list of items, inflate the source objects.

    Args:
        items (List[post.models.CollectionItem]): list of items to inflate
        organization_id (str): id of organization
        inflations (services.common.containers.InflationsV1): inflations for the items
        fields (services.common.containers.FieldsV1): fields for the items
        token (Optional[str]): service token

    Returns:
        List[services.post.containers.CollectionItemV1]

    """
    post_fields = utils.fields_for_item('post', fields)
    post_inflations = utils.inflations_for_item('post', inflations)

    source_dict = {}
    for item in items:
        source_dict.setdefault(item.source, {}).setdefault('ids', []).append(item.source_id)

    for source, data in source_dict.iteritems():
        if source == post_containers.CollectionItemV1.LUNO:
            posts = get_posts_with_fields(
                ids=data['ids'],
                organization_id=organization_id,
                fields=post_fields,
            )
            profile_id_to_profile = {}
            if utils.should_inflate_field('by_profile', post_inflations) and token:
                profile_ids = list(set([str(p.by_profile_id) for p in posts]))
                profiles = service.control.get_object(
                    service='profile',
                    action='get_profiles',
                    client_kwargs={'token': token},
                    return_object='profiles',
                    ids=profile_ids,
                    inflations={'disabled': True},
                )
                # XXX redundant use of protobuf_to_dict
                profile_id_to_profile = dict((p.id, protobuf_to_dict(p)) for p in profiles)

            for post in posts:
                source_dict[source].setdefault('objects', {})[str(post.id)] = {
                    'item': post,
                    'overrides': {
                        'by_profile': profile_id_to_profile.get(str(post.by_profile_id)),
                    },
                }

    containers = []
    for item in items:
        container = item.to_protobuf(
            inflations=inflations,
            fields=fields,
            collection_id=str(item.collection_id),
        )
        if item.source == post_containers.CollectionItemV1.LUNO:
            data = source_dict.get(item.source).get('objects', {}).get(str(item.source_id))
            if not data:
                continue

            post = data['item']
            overrides = data.get('overrides', {})
            post.to_protobuf(
                container.post,
                inflations=post_inflations,
                fields=post_fields,
                **overrides
            )
        containers.append(container)
    return containers


def get_collection_id_to_items_dict(
        collection_ids,
        number_of_items,
        organization_id,
        inflations,
        fields,
    ):
    """Get up to `number_of_items` items for the collections.

    When listing collections we can display a "preview" of whats in the
    collection, which means partially inflating the items within the
    collection.

    This will select up to `number_of_items` for the collection in the most
    optimal way possible based on fields and inflations.

    Args:
        collection_ids (List[str]): list of collection ids
        number_of_items (int): top number of items to return for each
            collection (based on position)
        organization_id (str): id of the organization
        inflations (services.common.containers.InflationsV1): inflations for the items
        fields (services.common.containers.FieldsV1): fields for the items

    Returns:
        dictionary of <collection_id>: <services.post.containers.CollectionItemV1>

    """
    queries = []
    parameters = {'organization_id': organization_id}
    # XXX come up with a way to cache this
    for index, collection_id in enumerate(collection_ids):
        collection_key = 'collection_id_%s' % (index,)
        parameters[collection_key] = collection_id
        query = (
            '(SELECT * FROM %s '
            'WHERE organization_id = %%(organization_id)s '
            'AND collection_id = %%(%s)s '
            'ORDER BY position LIMIT %d)'
        ) % (models.CollectionItem._meta.db_table, collection_key, int(number_of_items))
        queries.append(query)

    if not queries:
        return {}

    query = ' union all '.join(queries)
    items = list(models.CollectionItem.objects.raw(query, parameters))
    containers = inflate_items_source(
        items=items,
        organization_id=organization_id,
        inflations=inflations,
        fields=fields,
    )
    collections_dict = {}
    for container in containers:
        collections_dict.setdefault(container.collection_id, []).append(container)
    return collections_dict


def get_or_create_default_collection(owner_type, owner_id, organization_id):
    """Get or create the default collection.

    Args:
        owner_type (services.post.containers.PostV1.OwnerTypeV1): owner type
        owner_id (str): id of the owner
        organization_id (str): id of the organization

    Returns:
        models.Collection object

    """
    return models.Collection.objects.get_or_create(
        owner_type=owner_type,
        owner_id=owner_id,
        organization_id=organization_id,
        is_default=True,
    )


def get_display_names_for_collections(collections, token):
    """Get display names for the collections.

    Collections that are owned by teams are displayed as "[<Team Name>] <Collection Name>".

    Args:
        collections (List[services.post.containers.CollectionV1]): list of collections
        token (str): service token

    Returns:
        dict of <collection_id>: <display name>

    """
    team_ids = set([str(c.owner_id) for c in collections
                    if c.owner_type == post_containers.CollectionV1.TEAM])

    team_id_to_name = {}
    if team_ids:
        teams = service.control.get_object(
            service='team',
            action='get_teams',
            control={'paginator': {'page_size': len(team_ids)}},
            client_kwargs={'token': token},
            return_object='teams',
            inflations={'disabled': True},
            fields={'only': ['id', 'name']},
            ids=list(team_ids),
        )
        team_id_to_name = dict((t.id, t.name) for t in teams)

    collection_id_to_name = {}
    for collection in collections:
        name = collection.name
        if collection.is_default:
            name = 'Pinned Knowledge'

        if collection.owner_type == post_containers.CollectionV1.TEAM:
            team_name = team_id_to_name.get(str(collection.owner_id))
            if team_name:
                name = '[%s] %s' % (team_name, name)

        collection_id_to_name[str(collection.id)] = name
    return collection_id_to_name
