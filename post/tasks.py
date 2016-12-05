import logging

from protobufs.services.post import containers_pb2 as post_containers

from services.celery import app

from .models import Collection

logger = logging.getLogger(__name__)


@app.task
def ensure_default_collections():
    logger.info('ensuring default collections...')
    # XXX come up with a better way for this
    from profiles import models as profile_models
    from team import models as team_models
    profiles_with_no_default = profile_models.Profile.objects.nocache().exclude(
        id__in=Collection.objects.filter(
            owner_type=post_containers.CollectionV1.PROFILE,
            is_default=True,
        ).values_list('owner_id', flat=True),
    )
    collections = []
    if profiles_with_no_default:
        logger.info(
            '...%s profiles found without a default collection',
            len(profiles_with_no_default),
        )
        for profile in profiles_with_no_default:
            collection = Collection(
                owner_type=post_containers.CollectionV1.PROFILE,
                owner_id=profile.id,
                organization_id=profile.organization_id,
                is_default=True,
            )
            collections.append(collection)

    teams_with_no_default = team_models.Team.objects.nocache().exclude(
        id__in=Collection.objects.filter(
            owner_type=post_containers.CollectionV1.TEAM,
            is_default=True,
        ).values_list('owner_id', flat=True),
    )
    if teams_with_no_default:
        logger.info(
            '...%s teams found without a default collection',
            len(teams_with_no_default),
        )
        for team in teams_with_no_default:
            collection = Collection(
                owner_type=post_containers.CollectionV1.TEAM,
                owner_id=team.id,
                organization_id=team.organization_id,
                is_default=True,
            )
            collections.append(collection)

    if collections:
        logger.info('creating %s default collections', len(collections))
        Collection.objects.bulk_create(collections)
    else:
        logger.info('no default collections required')
