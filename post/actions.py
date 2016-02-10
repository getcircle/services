from protobufs.services.post import containers_pb2 as post_containers
from . import models


def create_collection(container, organization_id, by_profile_id):
    """Create a collection.

    Args:
        container (protobufs.services.post.containers.CollectionV1): protobuf
            container to convert into a model
        organization_id (uuid): organization id
        by_profile_id (uuid): profile id making the request

    Returns:

        post.models.Collection

    """
    profile_id = None
    if container.owner_type == post_containers.CollectionV1.TEAM:
        profile_id = by_profile_id
    elif container.owner_type == post_containers.CollectionV1.PROFILE:
        container.owner_id = by_profile_id

    return models.Collection.objects.from_protobuf(
        container,
        organization_id=organization_id,
        by_profile_id=profile_id,
    )
