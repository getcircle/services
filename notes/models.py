from common.db import models


class Note(models.UUIDModel, models.TimestampableModel):

    for_profile_id = models.UUIDField()
    owner_profile_id = models.UUIDField()
    content = models.TextField()
