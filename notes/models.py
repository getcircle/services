from common.db import models


class Note(models.UUIDModel, models.TimestampableModel):

    for_user = models.ForeignKey('users.User', related_name='+')
    user = models.ForeignKey('users.User')
    content = models.TextField()
