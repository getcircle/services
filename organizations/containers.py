

def copy_organization_to_container(organization, container):
    container.id = organization.pk.hex
    container.name = organization.name
    container.domain = organization.domain


def copy_team_to_container(team, container):
    container.id = team.pk.hex
    container.name = team.name
    container.owner_id = team.owner_id
    container.organization_id = team.organization_id
    container.path.extend(team.get_path())


def copy_address_to_container(address, container):
    container.id = address.pk.hex
    container.name = address.name
    container.address_1 = address.address_1
    container.address_2 = address.address_2
    container.city = address.city
    container.region = address.region
    container.postal_code = address.postal_code
    container.country_code = address.country_code
    container.organization_id = address.organization_id
