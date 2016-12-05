"""Script for generating fake users in dev for a team.

Run with:

    $ python manage.py runscript generate_members_for_team --script-args <domain> <team_id> <users> <role>

    ie.

    # generate members
    $ python manage.py runscript generate_members_for_team --script-args team 123 4 member

    # generate coordinators
    $ python manage.py runscript generate_members_for_team --script-args team 123 4 coordinator

"""
import logging

from django.conf import settings
from protobufs.services.team import containers_pb2 as team_containers

from organizations.models import Organization
from services.bootstrap import Bootstrap
from team.actions import add_members

from .generate_users import generate_fake_users

logger = logging.getLogger(__name__)


def run(domain, team_id, number_of_users, role):
    if not settings.DEBUG:
        logger.error('can\'t generate fake users in production')
        return

    roles = team_containers.TeamMemberV1.RoleV1.keys()
    try:
        role_type = roles.index(role.upper())
    except ValueError:
        logger.error('invalid role: %s, must be one of: %s', role, map(lambda x: x.lower(), roles))
        return

    Bootstrap.bootstrap()

    organization = Organization.objects.get(domain=domain)
    users = generate_fake_users(domain, number_of_users)
    members = []
    for user, profile in users:
        member = team_containers.TeamMemberV1(profile_id=str(profile.id), role=role_type)
        members.append(member)

    add_members(members, team_id, str(organization.id))

    logger.info(
        'generated %s users and added them to team %s as %s',
        number_of_users,
        team_id,
        role,
    )
