

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
