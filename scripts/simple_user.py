import logging

from organizations.models import Organization
from profiles.models import Profile
from users.models import User

from services.bootstrap import Bootstrap

logger = logging.getLogger(__name__)


def run(domain, first_name, last_name, email):
    Bootstrap.bootstrap()
    organization = Organization.objects.get(domain=domain)
    user = User.objects.create(primary_email=email)
    user.set_password('rhlabs')
    Profile.objects.create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        user_id=user.id,
        organization_id=organization.id,
    )
    logger.info('created %s in organization: %s', email, organization.domain)
