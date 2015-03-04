import django.db
from services.management.base import BaseCommand

from organizations import models as organization_models
from profiles import models as profile_models


class Command(BaseCommand):
    help = 'One-off migration to locations'

    def handle(self, *args, **options):
        addresses = organization_models.Address.objects.all()
        for address in addresses:
            print 'converting address: %s to location' % (address.name,)
            try:
                location = organization_models.Location.objects.create(
                    organization_id=address.organization_id,
                    name=address.name,
                    address_id=address.id,
                )
            except django.db.IntegrityError as e:
                print 'skipping address: %s | %s' % (address.name, e)
                continue

            profile_models.Profile.objects.filter(address_id=address.id).update(
                location_id=location.id,
                address_id=None,
            )
