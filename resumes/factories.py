from django_date_extensions.fields import ApproximateDate
from protobufs.resume_service_pb2 import ResumeService

from services.test import factory

from . import models


class CompanyFactory(factory.Factory):
    class Meta:
        model = models.Company
        protobuf = ResumeService.Containers.Company

    name = factory.FuzzyText()
    linkedin_id = factory.FuzzyUUID()


class EducationFactory(factory.Factory):
    class Meta:
        model = models.Education
        protobuf = ResumeService.Containers.Education

    user_id = factory.FuzzyUUID()
    school_name = factory.FuzzyText()
    start_date = ApproximateDate(year=2000)
    end_date = ApproximateDate(year=2001)
    notes = factory.FuzzyText()


class PositionFactory(factory.Factory):
    class Meta:
        model = models.Position
        protobuf = ResumeService.Containers.Position

    user_id = factory.FuzzyUUID()
    title = factory.FuzzyText()
    start_date = ApproximateDate(year=2006)
    end_date = ApproximateDate(year=2007)
    summary = factory.FuzzyText()
    company = factory.SubFactory(CompanyFactory)
