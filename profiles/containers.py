

def copy_profile_to_container(profile, container):
    container.id = profile.pk.hex
    container.organization_id = profile.organization_id
    container.user_id = profile.user_id
    container.address_id = profile.address_id
    container.title = profile.title
    container.work_phone = profile.work_phone
    container.image_url = profile.image_url
    container.location = profile.location
    container.email = profile.email
    container.team_id = profile.team_id
