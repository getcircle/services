from common.db import models


class Appreciation(models.UUIDModel, models.TimestampableModel, models.SafelyDeletableModel):

    source_profile_id = models.UUIDField(db_index=True)
    destination_profile_id = models.UUIDField(db_index=True)
    content = models.TextField()
