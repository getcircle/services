import service

from . import models


class CreateUser(service.Action):

    def run(self, *args, **kwargs):
        return models.User.objects.create()


class ValidUser(service.Action):

    user_id = service.UUIDType(required=True)

    def run(self, *args, **kwargs):
        return models.User.objects.filter(pk=self.user_id).exists()


class GetUser(service.Action):

    user_id = service.UUIDType(required=True)

    def run(self, *args, **kwargs):
        return models.User.objects.get_or_none(pk=self.user_id)
