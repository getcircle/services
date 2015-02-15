from protobufs.resume_service_pb2 import ResumeService
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
        self._verify_containers(educations[0], response.result.educations[0])
        self._verify_containers(educations[1], response.result.educations[1])

    def test_bulk_create_positions_invalid_user_id(self):
        position = mocks.mock_position(user_id='invalid')
        with self.assertFieldError('positions.0.user_id'):
            self.client.call_action('bulk_create_positions', positions=[position])

    def test_bulk_create_positions(self):
        positions = [mocks.mock_position(id=None), mocks.mock_position(id=None)]
        for position in positions:
            position.start_date.year = 2007
            position.start_date.month = 11
        response = self.client.call_action('bulk_create_positions', positions=positions)
        self.assertEqual(len(response.result.positions), len(positions))
        [self.assertTrue(position.id) for position in response.result.positions]
        self._verify_containers(positions[0], response.result.positions[0])
        self._verify_containers(positions[1], response.result.positions[1])

    def test_create_company(self):
        company = mocks.mock_company(id=None)
        response = self.client.call_action('create_company', company=company)
        self.assertTrue(response.result.company.id)
        self._verify_containers(company, response.result.company)

    def test_create_company_duplicate(self):
        company = factories.CompanyFactory.create_protobuf()
        duplicate_company = ResumeService.Containers.Company()
        duplicate_company.CopyFrom(company)
        duplicate_company.ClearField('id')
        response = self.client.call_action('create_company', company=duplicate_company)
        self._verify_containers(company, response.result.company)

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
        duplicate_company = ResumeService.Containers.Company()
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
