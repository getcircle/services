import datetime
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
    start_date = factory.FuzzyDate(datetime.date(2000, 1, 1))
    end_date = factory.FuzzyDate(datetime.date(2001, 1, 1))
    notes = factory.FuzzyText()


class PositionFactory(factory.Factory):
    class Meta:
        model = models.Position
        protobuf = ResumeService.Containers.Position

    user_id = factory.FuzzyUUID()
    title = factory.FuzzyText()
    start_date = factory.FuzzyDate(datetime.date(2006, 1, 1))
    end_date = factory.FuzzyDate(datetime.date(2007, 1, 1))
    summary = factory.FuzzyText()
    company = factory.SubFactory(CompanyFactory)
