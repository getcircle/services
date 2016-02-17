import service.control

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class Test(MockedTestCase):

    def setUp(self):
        super(Test, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = factories.ProfileFactory.create(organization_id=self.organization.id)
        self.token = mocks.mock_token(
            organization_id=self.organization.id,
            profile_id=str(self.profile.id),
        )
        self.client = service.control.Client('profile', token=self.token)
        self.mock.instance.dont_mock_service('profile')

    def test_get_reporting_details_profile_id_required(self):
        with self.assertFieldError('profile_id', 'MISSING'):
            self.client.call_action('get_reporting_details')

    def test_get_reporting_details_profile_id_invalid(self):
        with self.assertFieldError('profile_id'):
            self.client.call_action('get_reporting_details', profile_id='invalid')

    def test_get_reporting_details_wrong_organization(self):
        profile = factories.ProfileFactory.create()
        manager = factories.ProfileFactory.create(organization_id=profile.organization_id)
        manager_node = factories.ReportingStructureFactory.create(
            profile=manager,
        )
        factories.ReportingStructureFactory.create(
            profile=profile,
            manager=manager_node,
        )
        response = self.client.call_action('get_reporting_details', profile_id=str(profile.id))
        details = response.result.details
        self.assertFalse(details.manager.ByteSize())
        self.assertFalse(details.peers)
        self.assertFalse(details.direct_reports)

    def test_get_reporting_details(self):
        manager = factories.ReportingStructureFactory.create(
            organization_id=self.organization.id,
            profile__organization_id=self.organization.id,
        )
        node = factories.ReportingStructureFactory.create(manager=manager, profile=self.profile)

        # add 3 peers
        factories.ReportingStructureFactory.create_batch(
            size=3,
            manager=manager,
            organization_id=self.organization.id,
            profile__organization_id=self.organization.id,
        )

        # add 4 direct reports
        factories.ReportingStructureFactory.create_batch(
            size=4,
            manager=node,
            organization_id=self.organization.id,
            profile__organization_id=self.organization.id,
        )

        response = self.client.call_action(
            'get_reporting_details',
            profile_id=str(self.profile.id),
        )
        details = response.result.details
        self.assertTrue(details.manager.ByteSize())
        self.assertEqual(len(details.peers), 3)
        self.assertEqual(len(details.direct_reports), 4)

    def test_get_reporting_details_inflations(self):
        manager = factories.ReportingStructureFactory.create(
            organization_id=self.organization.id,
            profile__organization_id=self.organization.id,
        )
        node = factories.ReportingStructureFactory.create(manager=manager, profile=self.profile)

        # add 3 peers
        factories.ReportingStructureFactory.create_batch(
            size=3,
            manager=manager,
            organization_id=self.organization.id,
            profile__organization_id=self.organization.id,
        )

        # add 4 direct reports
        factories.ReportingStructureFactory.create_batch(
            size=4,
            manager=node,
            organization_id=self.organization.id,
            profile__organization_id=self.organization.id,
        )

        response = self.client.call_action(
            'get_reporting_details',
            profile_id=str(self.profile.id),
            fields={'only': [
                'details.manager.id',
                'details.[]peers.id',
                'details.[]direct_reports.id',
            ]},
        )
        details = response.result.details
        self.assertTrue(details.manager.id)
        self.assertFalse(details.manager.full_name)
        for peer in details.peers:
            self.assertTrue(peer.id)
            self.assertFalse(peer.full_name)

        for direct_report in details.direct_reports:
            self.assertTrue(direct_report.id)
            self.assertFalse(direct_report.full_name)
