from common.db import models


class Company(models.UUIDModel, models.TimestampableModel):

    name = models.CharField(max_length=255, unique=True)
    linkedin_id = models.CharField(max_length=255, null=True)


class Education(models.UUIDModel, models.TimestampableModel):

    user_id = models.UUIDField(db_index=True)
    school_name = models.CharField(max_length=255)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    notes = models.TextField(null=True)


class Position(models.UUIDModel, models.TimestampableModel):

    user_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=255)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    summary = models.TextField(null=True)
    company = models.ForeignKey(Company, null=True)
