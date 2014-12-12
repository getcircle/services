import service

import identities as identity_constants


class IdentityContainer(service.Container):

    id = service.UUIDType()
    user_id = service.UUIDType()
    first_name = service.StringType()
    last_name = service.StringType()
    type = service.StringType()
    email = service.EmailType()
    phone_number = service.PhoneNumberType()

    @classmethod
    def from_model(cls, model):
        container = cls()
        container.id = model.pk.hex
        user_id = model.user_id
        if hasattr(user_id, 'hex'):
            user_id = user_id.hex

        container.user_id = user_id
        container.first_name = model.first_name
        container.last_name = model.last_name
        container.type = (
            identity_constants.IDENTITY_TYPE_TO_NAME_MAP[model.type]
        )
        container.email = model.email
        if model.phone_number:
            container.phone_number = str(model.phone_number)

        container.validate()
        return container
