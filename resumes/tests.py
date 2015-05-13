from protobufs.services.resume import containers_pb2 as resume_containers
import service.control

from services.test import (
    fuzzy,
    TestCase,
    mocks,
)

from . import (
    factories,
    models,
)


class TestResumes(TestCase):

    def setUp(self):
        super(TestResumes, self).setUp()
        self.client = service.control.Client('resume', token='test-token')

    def test_bulk_create_educations_invalid_user_id(self):
        education = mocks.mock_education(user_id='invalid')
        with self.assertFieldError('educations.0.user_id'):
            self.client.call_action('bulk_create_educations', educations=[education])

    def test_bulk_create_educations_invalid_user_id_second_item(self):
        educations = [
            mocks.mock_education(),
            mocks.mock_education(user_id='invalid'),
        ]
        with self.assertFieldError('educations.1.user_id'):
            self.client.call_action('bulk_create_educations', educations=educations)

    def test_bulk_create_educations(self):
        educations = [mocks.mock_education(id=None), mocks.mock_education(id=None)]
        response = self.client.call_action('bulk_create_educations', educations=educations)
        self.assertEqual(len(response.result.educations), len(educations))
        [self.assertTrue(education.id) for education in response.result.educations]
        educations_by_name = dict((education.school_name, education) for education in educations)
        for education in response.result.educations:
            self.verify_containers(educations_by_name[education.school_name], education)

    def test_bulk_create_educations_duplicates(self):
        education = factories.EducationFactory.create_protobuf()
        duplicate_education = resume_containers.EducationV1()
        duplicate_education.CopyFrom(education)
        duplicate_education.ClearField('id')
        duplicate_same_request = mocks.mock_education(id=None)
        response = self.client.call_action(
            'bulk_create_educations',
            educations=[
                duplicate_education,
                duplicate_same_request,
                duplicate_same_request,
                mocks.mock_education(id=None),
            ],
        )
        self.assertEqual(len(response.result.educations), 3)

        self.verify_containers(education, response.result.educations[0])
        educations = models.Education.objects.all()
        self.assertEqual(len(educations), 3)

    def test_bulk_create_positions_invalid_user_id(self):
        position = mocks.mock_position(user_id='invalid')
        with self.assertFieldError('positions.0.user_id'):
            self.client.call_action('bulk_create_positions', positions=[position])

    def test_bulk_create_positions(self):
        company = factories.CompanyFactory.create_protobuf()
        positions = [
            mocks.mock_position(id=None, company=company),
            mocks.mock_position(id=None, company=company),
        ]
        for position in positions:
            position.start_date.year = 2007
            position.start_date.month = 11
        response = self.client.call_action('bulk_create_positions', positions=positions)
        self.assertEqual(len(response.result.positions), len(positions))
        [self.assertTrue(position.id) for position in response.result.positions]
        positions_by_title = dict((position.title, position) for position in positions)
        for position in response.result.positions:
            self.verify_containers(positions_by_title[position.title], position)

    def test_bulk_create_positions_duplicates(self):
        company = factories.CompanyFactory.create_protobuf()
        position = factories.PositionFactory.build()
        position.company_id = company.id
        position.save()
        duplicate_position = resume_containers.PositionV1()
        position.to_protobuf(duplicate_position)
        duplicate_position.ClearField('id')
        duplicate_position.company.CopyFrom(company)
        duplicate_same_request = mocks.mock_position(id=None, company=company)
        response = self.client.call_action(
            'bulk_create_positions',
            positions=[
                duplicate_position,
                duplicate_same_request,
                duplicate_same_request,
                mocks.mock_position(id=None, company=company),
            ],
        )
        self.assertEqual(len(response.result.positions), 3)
        positions_by_title = dict(
            (position.title, position) for position in response.result.positions
        )

        positions = models.Position.objects.all()
        self.assertEqual(len(positions), 3)
        duplicate_position.id = position.id.hex
        self.verify_containers(duplicate_position, positions_by_title[position.title])

    def test_create_company(self):
        company = mocks.mock_company(id=None)
        response = self.client.call_action('create_company', company=company)
        self.assertTrue(response.result.company.id)
        self.verify_containers(company, response.result.company)

    def test_create_company_duplicate(self):
        company = factories.CompanyFactory.create_protobuf()
        duplicate_company = resume_containers.CompanyV1()
        duplicate_company.CopyFrom(company)
        duplicate_company.ClearField('id')
        response = self.client.call_action('create_company', company=duplicate_company)
        self.verify_containers(company, response.result.company)

    def test_get_resume_invalid_user_id(self):
        with self.assertFieldError('user_id'):
            self.client.call_action('get_resume', user_id='invalid')

    def test_get_resume(self):
        user_id = fuzzy.FuzzyUUID().fuzz()
        company = factories.CompanyFactory.create()
        positions = factories.PositionFactory.create_batch(
            size=3,
            user_id=user_id,
            company=company,
        )
        educations = factories.EducationFactory.create_batch(size=3, user_id=user_id)
        response = self.client.call_action('get_resume', user_id=user_id)
        self.assertEqual(len(response.result.resume.positions), len(positions))
        self.assertEqual(len(response.result.resume.educations), len(educations))

    def test_bulk_create_companies(self):
        companies = [mocks.mock_company(id=None), mocks.mock_company(id=None)]
        response = self.client.call_action('bulk_create_companies', companies=companies)
        self.assertEqual(len(response.result.companies), len(companies))

    def test_bulk_create_companies_duplicates(self):
        company = factories.CompanyFactory.create_protobuf()
        duplicate_company = resume_containers.CompanyV1()
        duplicate_company.CopyFrom(company)
        duplicate_company.ClearField('id')

        duplicate_same_request = mocks.mock_company(id=None)
        companies = [
            duplicate_company,
            duplicate_same_request,
            duplicate_same_request,
            mocks.mock_company(id=None),
        ]
        response = self.client.call_action('bulk_create_companies', companies=companies)
        self.assertEqual(len(response.result.companies), 3)

        companies = models.Company.objects.all()
        self.assertEqual(len(companies), 3)

    def test_bulk_create_educations_user_id_required(self):
        education = mocks.mock_education(id=None, user_id=None)
        with self.assertFieldError('educations.0.user_id'):
            self.client.call_action('bulk_create_educations', educations=[education])
