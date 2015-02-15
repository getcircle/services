from service import (
    actions,
    validators,
)

from . import models


class BulkCreateEducations(actions.Action):

    def validate(self, *args, **kwargs):
        super(BulkCreateEducations, self).validate(*args, **kwargs)
        if not self.is_error():
            for index, education in enumerate(self.request.educations):
                if not validators.is_uuid4(education.user_id):
                    self.note_field_error('educations.%s.user_id' % (index,), 'INVALID')

    def run(self, *args, **kwargs):
        objects = [models.Education.objects.from_protobuf(
            education,
            commit=False,
        ) for education in self.request.educations]
        educations = models.Education.objects.bulk_create(objects)
        for education in educations:
            container = self.response.educations.add()
            education.to_protobuf(container)


class BulkCreatePositions(actions.Action):

    def validate(self, *args, **kwargs):
        super(BulkCreatePositions, self).validate(*args, **kwargs)
        if not self.is_error():
            for index, position in enumerate(self.request.positions):
                if not validators.is_uuid4(position.user_id):
                    self.note_field_error('positions.%s.user_id' % (index,), 'INVALID')

    def run(self, *args, **kwargs):
        objects = [models.Position.objects.from_protobuf(
            position,
            commit=False,
            company_id=position.company.id,
        ) for position in self.request.positions]
        positions = models.Position.objects.bulk_create(objects)
        for index, position in enumerate(positions):
            container = self.response.positions.add()
            position.to_protobuf(container)
            container.company.CopyFrom(self.request.positions[index].company)


class CreateCompany(actions.Action):

    def run(self, *args, **kwargs):
        companies = BulkCreateCompanies.bulk_create_companies([self.request.company])
        companies[0].to_protobuf(self.response.company)


class BulkCreateCompanies(actions.Action):

    @staticmethod
    def bulk_create_companies(protobufs):
        companies = dict((company.name, company) for company in protobufs)
        names = companies.keys()
        companies = companies.values()
        objects = [models.Company.objects.from_protobuf(
            company,
            commit=False,
        ) for company in companies]
        models.Company.objects.bulk_create(objects)
        return models.Company.objects.filter(name__in=names)

    def run(self, *args, **kwargs):
        companies = self.bulk_create_companies(self.request.companies)
        for company in companies:
            container = self.response.companies.add()
            company.to_protobuf(container)


class GetResume(actions.Action):

    type_validators = {
        'user_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        educations = models.Education.objects.filter(
            user_id=self.request.user_id,
        )
        positions = models.Position.objects.select_related('company').filter(
            user_id=self.request.user_id,
        )

        resume = self.response.resume
        resume.user_id = self.request.user_id
        for education in educations:
            container = resume.educations.add()
            education.to_protobuf(container)

        for position in positions:
            container = resume.positions.add()
            position.company.to_protobuf(container.company)
            position.to_protobuf(container)
