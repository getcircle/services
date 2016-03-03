"""Script to migrate from old teams to new teams.

"""
import logging

from organizations import models as organization_models
from profiles import models as profile_models
from services.bootstrap import Bootstrap

logger = logging.getLogger(__name__)


def run():
    Bootstrap.bootstrap()

    reporting_nodes = organization_models.ReportingStructure.objects.all()

    profile_ids = [node.profile_id for node in reporting_nodes]
    profiles = profile_models.Profile.objects.filter(id__in=profile_ids)
    profile_dict = dict((str(profile.id), profile) for profile in profiles)

    for node in reporting_nodes:
        profile = profile_dict[str(node.profile_id)]
        if str(profile.organization_id) != str(node.organization_id):
            node.organization_id = profile.organization_id
            logger.info(
                'updating node to match profile: %s with organization_id: %s',
                node.profile_id,
                profile.organization_id,
            )
            node.save()
