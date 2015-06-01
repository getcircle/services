import service.control

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)

from .. import (
    factories,
    models,
)


class TestGlossaryTerm(TestCase):

    def setUp(self):
        super(TestGlossaryTerm, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.client = service.control.Client(
            'glossary',
            token=mocks.mock_token(
                organization_id=self.organization.id,
                profile_id=self.profile.id,
            ),
        )

    def test_create_term_term_required(self):
        with self.assertFieldError('term', 'MISSING'):
            self.client.call_action('create_term')

    def test_create_term_term_required_fields(self):
        term = factories.TermFactory.build()
        with self.assertFieldError('term.name', 'MISSING'):
            self.client.call_action(
                'create_term',
                term=term.as_dict(exclude=('name',)),
            )

        with self.assertFieldError('term.definition', 'MISSING'):
            self.client.call_action(
                'create_term',
                term=term.as_dict(exclude=('definition',)),
            )

    def test_create_term(self):
        expected = factories.TermFactory.build_protobuf(
            created_by_profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        response = self.client.call_action('create_term', term=expected)
        self.verify_containers(expected, response.result.term)
        term = models.Term.objects.get(pk=response.result.term.id)
        self.verify_containers(response.result.term, term.to_protobuf())

    def test_create_term_ignore_term_organization_id(self):
        expected = factories.TermFactory.build_protobuf(
            organization_id=fuzzy.FuzzyUUID().fuzz(),
        )
        response = self.client.call_action('create_term', term=expected)
        self.assertNotEqualUUID4(expected.organization_id, response.result.term.organization_id)
        self.assertEqualUUID4(response.result.term.organization_id, str(self.organization.id))

    def test_update_term_term_required(self):
        with self.assertFieldError('term', 'MISSING'):
            self.client.call_action('update_term')

    def test_update_term_term_required_fields(self):
        term = factories.TermFactory.create()
        with self.assertFieldError('term.id', 'MISSING'):
            self.client.call_action(
                'update_term',
                term=term.as_dict(exclude=('id',)),
            )

        with self.assertFieldError('term.name', 'MISSING'):
            self.client.call_action(
                'update_term',
                term=term.as_dict(exclude=('name',)),
            )

        with self.assertFieldError('term.definition', 'MISSING'):
            self.client.call_action(
                'update_term',
                term=term.as_dict(exclude=('definition',)),
            )

    def test_update_term(self):
        expected = factories.TermFactory.create(
            created_by_profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        data = expected.as_dict()
        data['name'] = 'new name'
        response = self.client.call_action('update_term', term=data)
        self.assertEqual(response.result.term.name, 'new name')
        term = models.Term.objects.get(pk=response.result.term.id)
        self.verify_containers(response.result.term, term.to_protobuf())

    def test_update_term_id_invalid(self):
        with self.assertFieldError('term.id'):
            self.client.call_action(
                'update_term',
                term={'id': 'invalid', 'name': 'test', 'definition': 'test'},
            )

    def test_update_term_update_organization_id_fails(self):
        expected = factories.TermFactory.create(
            created_by_profile_id=self.profile.id,
            organization_id=self.organization.id,
        )
        data = expected.as_dict()
        data['organization_id'] = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action('update_term', term=data)
        self.assertNotEqualUUID4(data['organization_id'], response.result.term.organization_id)
        self.assertEqualUUID4(str(expected.organization_id), response.result.term.organization_id)

    def test_get_term_by_id(self):
        expected = factories.TermFactory.create_protobuf(organization_id=self.organization.id)
        response = self.client.call_action('get_term', id=expected.id)
        self.verify_containers(expected, response.result.term)

    def test_get_term_by_id_wrong_organization(self):
        expected = factories.TermFactory.create_protobuf()
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_term', id=expected.id)

    def test_get_term_by_name_does_not_exist(self):
        with self.assertFieldError('name', 'DOES_NOT_EXIST'):
            self.client.call_action('get_term', name='does_not_exist')

    def test_get_term_by_name_wrong_organization(self):
        expected = factories.TermFactory.create_protobuf()
        with self.assertFieldError('name', 'DOES_NOT_EXIST'):
            self.client.call_action('get_term', name=expected.name)

    def test_get_term_by_id_does_not_exist(self):
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('get_term', id=fuzzy.FuzzyUUID().fuzz())

    def test_get_terms(self):
        # create terms for another organization
        factories.TermFactory.create_batch(size=2)
        terms = factories.TermFactory.create_batch(size=3, organization_id=self.organization.id)
        response = self.client.call_action('get_terms')
        self.assertEqual(len(terms), len(response.result.terms))

    def test_get_terms_with_ids_wrong_organization(self):
        # create terms for another organization
        terms = factories.TermFactory.create_batch(
            size=2,
            organization_id=fuzzy.FuzzyUUID().fuzz(),
        )
        response = self.client.call_action('get_terms', ids=[str(term.id) for term in terms])
        self.assertEqual(len(response.result.terms), 0)

    def test_get_terms_invalid_ids(self):
        with self.assertFieldError('ids'):
            self.client.call_action('get_terms', ids=['invalid', 'invalid'])

    def test_get_terms_by_ids(self):
        terms = factories.TermFactory.create_batch(size=3, organization_id=self.organization.id)
        response = self.client.call_action('get_terms', ids=[str(terms[0].id)])
        self.assertEqual(len(response.result.terms), 1)
        self.verify_containers(response.result.terms[0], terms[0].to_protobuf())

    def test_delete_term_invalid_id(self):
        with self.assertFieldError('id'):
            self.client.call_action('delete_term', id='invalid')

    def test_delete_term_id_required(self):
        with self.assertFieldError('id', 'MISSING'):
            self.client.call_action('delete_term')

    def test_delete_term_does_not_exist(self):
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_term', id=fuzzy.FuzzyUUID().fuzz())

    def test_delete_term_wrong_organization_id(self):
        term = factories.TermFactory.create_protobuf()
        with self.assertFieldError('id', 'DOES_NOT_EXIST'):
            self.client.call_action('delete_term', id=term.id)

    def test_delete_term(self):
        terms = factories.TermFactory.create_batch(size=3, organization_id=self.organization.id)
        self.client.call_action('delete_term', id=str(terms[0].id))

        self.assertFalse(models.Term.objects.filter(id=terms[0].id).exists())
        self.assertEqual(len(models.Term.objects.filter(organization_id=self.organization.id)), 2)
