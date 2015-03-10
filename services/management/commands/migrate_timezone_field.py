from services.management.base import BaseCommand
from services.utils import get_timezone_for_location
from organizations import models


class Command(BaseCommand):
    help = 'One-off migration to update the timezone field for an address'

    def handle(self, *args, **options):
        addresses = models.Address.objects.all()
        for address in addresses:
            print 'adding timezone to address: %s' % (address.name,)
            address.timezone = get_timezone_for_location(address.latitude, address.longitude)
            address.save()
