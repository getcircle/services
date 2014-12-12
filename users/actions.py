import service

from . import models


class CreateUser(service.Action):

    user_id = service.UUIDType()

    def run(self, *args, **kwargs):
        user = models.User.objects.create()
        self.user_id = user.id.hex


class ValidUser(service.Action):

    user_id = service.UUIDType(required=True)

    exists = service.BooleanType(default=False)

    def run(self, *args, **kwargs):
        self.exists = models.User.objects.filter(pk=self.user_id).exists()
