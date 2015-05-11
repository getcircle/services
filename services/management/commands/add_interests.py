import random
import service.control

from services.management.base import BaseCommand
from services.token import make_admin_token

from protobufs.services.profile import containers_pb2 as profile_containers

from organizations import models as organization_models
from profiles import models as profile_models


class Command(BaseCommand):
    help = 'One-off to add skills to profiles in an organization'
    args = '<organization_domain>'

    def handle(self, *args, **options):
        organization = organization_models.Organization.objects.get(domain=args[0])
        client = service.control.Client(
            'profile',
            token=make_admin_token(organization_id=str(organization.id)),
        )
        interests = profile_models.Tag.objects.filter(
            organization_id=organization.id,
            type=profile_containers.TagV1.INTEREST,
        )
        interest_containers = []
        for interest in interests:
            container = profile_containers.TagV1()
            interest.to_protobuf(container)
            interest_containers.append(container)

        profiles = profile_models.Profile.objects.filter(organization_id=organization.id)
        for profile in profiles:
            profile_interests = []
            for _ in range(random.randrange(0, 15)):
                interest = random.choice(interest_containers)
                if interest not in profile_interests:
                    profile_interests.append(interest)
            client.call_action('add_tags', profile_id=str(profile.id), tags=profile_interests)
