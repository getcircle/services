from common.db import models
from django_date_extensions.fields import ApproximateDateField


def approximate_date_as_dict(approximate_date):
    output = {}
    if approximate_date.year:
        output['year'] = approximate_date.year
    if approximate_date.month:
        output['month'] = approximate_date.month
    if approximate_date.day:
        output['day'] = approximate_date.day
    return output


class Company(models.UUIDModel, models.TimestampableModel):

    name = models.CharField(max_length=255, unique=True)
    linkedin_id = models.CharField(max_length=255, null=True)


class ApproximateDateAsDictMixin(object):

    as_dict_value_transforms = {
        'end_date': approximate_date_as_dict,
        'start_date': approximate_date_as_dict,
    }

    def as_dict(self, *args, **kwargs):
        output = super(ApproximateDateAsDictMixin, self).as_dict(*args, **kwargs)
        if output.get('end_date', '') is None:
            output.pop('end_date')

        if output.get('start_date', '') is None:
            output.pop('start_date')
        return output


class Education(ApproximateDateAsDictMixin, models.UUIDModel, models.TimestampableModel):

    user_id = models.UUIDField(db_index=True)
    school_name = models.CharField(max_length=255)
    start_date = ApproximateDateField(max_length=10, null=True)
    end_date = ApproximateDateField(max_length=10, null=True)
    notes = models.TextField(null=True)


class Position(ApproximateDateAsDictMixin, models.UUIDModel, models.TimestampableModel):

    user_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=255)
    start_date = ApproximateDateField(max_length=10, null=True)
    end_date = ApproximateDateField(max_length=10, null=True)
    summary = models.TextField(null=True)
    company = models.ForeignKey(Company, null=True)
