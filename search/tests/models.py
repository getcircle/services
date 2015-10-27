from common.db import models


class TestSearchModel(models.UUIDModel):
    title = models.CharField(max_length=64)
    content = models.CharField(max_length=255)
