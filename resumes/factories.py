from django_date_extensions.fields import ApproximateDate
from protobufs.services.resume import containers_pb2 as resume_containers

from services.test import factory

from . import models


class CompanyFactory(factory.Factory):
    class Meta:
        model = models.Company
        protobuf = resume_containers.CompanyV1

    name = factory.FuzzyText()
    linkedin_id = factory.FuzzyUUID()


class EducationFactory(factory.Factory):
    class Meta:
        model = models.Education
        protobuf = resume_containers.EducationV1

    user_id = factory.FuzzyUUID()
    school_name = factory.FuzzyText()
    start_date = ApproximateDate(year=2000)
    end_date = ApproximateDate(year=2001)
    notes = factory.FuzzyText()


class PositionFactory(factory.Factory):
    class Meta:
        model = models.Position
        protobuf = resume_containers.PositionV1

    user_id = factory.FuzzyUUID()
    title = factory.FuzzyText()
    start_date = ApproximateDate(year=2006)
    end_date = ApproximateDate(year=2007)
    summary = factory.FuzzyText()
    company = factory.SubFactory(CompanyFactory)
