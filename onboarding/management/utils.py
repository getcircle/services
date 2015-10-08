import service.control

from services.token import make_admin_token


def get_token_for_domain(domain):
    organization = service.control.get_object(
        service='organization',
        action='get_organization',
        client_kwargs={'token': make_admin_token()},
        return_object='organization',
        domain=domain,
    )
    return make_admin_token(organization_id=organization.id)
