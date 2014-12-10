from . import (
    models,
    serializers,
)


def create_identity(user_id, identity_type, data):
    data['user'] = user_id
    identity = serializers.IdentitySerializer(data=data)
    if not identity.is_valid():
        return None
    return models.Identity.objects.create(**identity.validated_data)
