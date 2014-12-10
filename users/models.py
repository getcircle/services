from common.db import models


class User(models.UUIDModel, models.TimestampableModel):
    pass
