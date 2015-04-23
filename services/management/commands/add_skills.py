import random
import service.control
from services.management.base import BaseCommand

from protobufs.services.profile import containers_pb2 as profile_containers

from organizations import models as organization_models
from profiles import models as profile_models


class Command(BaseCommand):
    help = 'One-off to add skills to profiles in an organization'
    args = '<organization_domain>'

    def handle(self, *args, **options):
        client = service.control.Client('profile', token='admin-token')
        organization = organization_models.Organization.objects.get(domain=args[0])
        skills = profile_models.Tag.objects.filter(
            organization_id=organization.id,
            type=profile_containers.TagV1.SKILL,
        )
        skill_containers = []
        for skill in skills:
            container = profile_containers.TagV1()
            skill.to_protobuf(container)
            skill_containers.append(container)
        profiles = profile_models.Profile.objects.filter(organization_id=organization.id)
        for profile in profiles:
            profile_skills = []
            for _ in range(random.randrange(0, 15)):
                skill = random.choice(skill_containers)
                if skill not in profile_skills:
                    profile_skills.append(skill)
            client.call_action('add_tags', profile_id=str(profile.id), tags=profile_skills)
