from users import models
from services.management.base import (
    BaseCommand,
    CommandError,
)


class Command(BaseCommand):
    args = '<user primary_email> <fields>...'
    help = 'Updates the given user based on fields'

    def handle(self, *args, **options):
        primary_email = args[0]
        user = models.User.objects.get(primary_email=primary_email)
        for field in args[1:]:
            try:
                key, value = field.split('=')
            except ValueError:
                raise CommandError('Invalid field: %s' % (field,))

            if hasattr(user, key):
                setattr(user, key, value)
            else:
                raise CommandError('User doesn\'t have field: %s' % (field,))

        user.save()
        print 'User updated: %s' % (user.as_dict(),)
