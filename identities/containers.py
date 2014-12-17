

def copy_model_to_container(model, identity):
    identity.id = model.pk.hex
    user_id = model.user_id
    if hasattr(user_id, 'hex'):
        user_id = user_id.hex

    identity.user_id = user_id
    identity.first_name = model.first_name
    identity.last_name = model.last_name
    identity.type = model.type
    identity.email = model.email
    if model.phone_number:
        identity.phone_number = str(model.phone_number)
