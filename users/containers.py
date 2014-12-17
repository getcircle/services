

def copy_model_to_container(model, container):
    container.id = model.pk.hex
    container.primary_email = model.primary_email
    container.is_active = model.is_active
    container.is_admin = model.is_admin
