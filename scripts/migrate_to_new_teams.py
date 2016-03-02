"""Script to migrate from old teams to new teams.

"""
import logging

from django.db.models import Q
from protobufs.services.team import containers_pb2 as team_containers
from organizations import models as organization_models
from team import models as team_models
from services.bootstrap import Bootstrap

logger = logging.getLogger(__name__)


def run():
    Bootstrap.bootstrap()
    # grab every old organization team, for each team, the coordinator should
    # be the manager, the children should be the members

    # exclude red ventures
    old_teams = organization_models.Team.objects.exclude(
        Q(organization_id='b7c3c68f-81ff-48ca-b7fa-4dc86d3206c5') |
        Q(name=None)
    )
    members_to_create = []
    logger.info('migrating %s old teams', len(old_teams))
    for old_team in old_teams:
        try:
            manager = organization_models.ReportingStructure.objects.get(
                organization_id=old_team.organization_id,
                profile_id=old_team.manager_profile_id,
            )
        except organization_models.ReportingStructure.DoesNotExist:
            logger.info('no manager node found for: %s', old_team.manager_profile_id)
            continue

        reports = manager.get_children()

        team = team_models.Team.objects.create(
            organization_id=old_team.organization_id,
            name=old_team.name,
            description=old_team.description,
        )
        logger.info('converting team: %s to new team: %s', old_team.id, team.id)
        coordinator = team_models.TeamMember(
            role=team_containers.TeamMemberV1.COORDINATOR,
            team=team,
            profile_id=manager.profile_id,
            organization_id=team.organization_id,
        )
        members_to_create.append(coordinator)
        logger.info('converting manager to team coordinator: %s', coordinator.profile_id)

        for report in reports:
            member = team_models.TeamMember(
                role=team_containers.TeamMemberV1.MEMBER,
                team=team,
                profile_id=report.profile_id,
                organization_id=report.organization_id,
            )
            logger.info('converting direct report to member: %s', report.profile_id)
            members_to_create.append(member)

    logger.info('creating %s team members', len(members_to_create))
    team_models.TeamMember.objects.bulk_create(members_to_create)
