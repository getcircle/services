import common.utils
from . import models


def create_user():
    return models.User.objects.create()


def get_user(user_id):
    uuid = common.utils.uuid_from_hex(user_id)
    if uuid is None:
        return None

    return models.User.objects.get_or_none(pk=uuid)
