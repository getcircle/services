from common.db import models


class Note(models.UUIDModel, models.TimestampableModel):

    DELETED_STATUS = 1
    STATUS_CHOICES = (
        (DELETED_STATUS, 'Deleted'),
    )

    for_profile_id = models.UUIDField()
    owner_profile_id = models.UUIDField()
    content = models.TextField()
    status = models.PositiveSmallIntegerField(null=True, choices=STATUS_CHOICES)
