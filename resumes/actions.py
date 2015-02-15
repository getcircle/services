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

    @staticmethod
    def _build_unique_key(education):
        return '%s.%s.%s.%s' % (
            education.user_id,
            education.school_name,
            str(education.start_date),
            str(education.end_date),
        )

    @classmethod
    def bulk_create_educations(cls, protobufs):
        objects = [models.Education.objects.from_protobuf(
            education,
            commit=False,
        ) for education in protobufs]
        educations = dict(
            (cls._build_unique_key(education), education) for education in objects
        ).values()
        models.Education.objects.bulk_create(educations)

        user_ids = set()
        school_names = set()
        start_dates = set()
        end_dates = set()
        for education in educations:
            user_ids.add(education.user_id)
            school_names.add(education.school_name)
            start_dates.add(education.start_date)
            end_dates.add(education.end_date)

        return models.Education.objects.filter(
            user_id__in=user_ids,
            school_name__in=school_names,
            start_date__in=start_dates,
            end_date__in=end_dates,
        )

    def run(self, *args, **kwargs):
        educations = self.bulk_create_educations(self.request.educations)
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

    @staticmethod
    def _build_unique_key(position):
        return '%s.%s.%s' % (
            position.user_id,
            position.title,
            position.company_id,
        )

    @classmethod
    def bulk_create_positions(cls, protobufs):
        objects = [models.Position.objects.from_protobuf(
            position,
            commit=False,
            company_id=position.company.id,
        ) for position in protobufs]
        positions = dict(
            (cls._build_unique_key(position), position) for position in objects
        ).values()
        models.Position.objects.bulk_create(positions)

        user_ids = set()
        titles = set()
        company_ids = set()
        for position in positions:
            user_ids.add(position.user_id)
            titles.add(position.title)
            company_ids.add(position.company_id)

        return models.Position.objects.select_related('company').filter(
            user_id__in=user_ids,
            title__in=titles,
            company_id__in=filter(None, company_ids),
        )

    def run(self, *args, **kwargs):
        positions = self.bulk_create_positions(self.request.positions)
        for position in positions:
            container = self.response.positions.add()
            position.to_protobuf(container)
            position.company.to_protobuf(container.company)


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
