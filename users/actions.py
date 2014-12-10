from . import models


def create_user():
    return models.User.objects.create()
