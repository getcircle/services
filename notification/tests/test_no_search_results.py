import mock
from protobufs.services.user.containers import token_pb2
import service.control
from service.transports.mock import get_mockable_response

from services.test import (
    fuzzy,
    mocks,
    MockedTestCase,
)

from .. import factories


class TestNoSearchResults(MockedTestCase):

    def setUp(self):
        super(TestNoSearchResults, self).setUp()
        self.organization = mocks.mock_organization()
        self.profile = mocks.mock_profile(organization_id=self.organization.id)
        self.client = service.control.Client(
            'notification',
            token=mocks.mock_token(
                profile_id=self.profile.id,
                organization_id=self.organization.id,
            ),
        )
        self.mock.instance.dont_mock_service('notification')

    def _setup_mocks(self):
        self.mock.instance.register_mock_object(
            service='organization',
            action='get_organization',
            return_object=self.organization,
            return_object_path='organization',
        )
        response = get_mockable_response('organization', 'get_profile_reporting_details')
        manager = mocks.mock_profile(organization_id=self.organization.id)
        response.manager_profile_id = manager.id
        self.mock.instance.register_mock_response(
            service='organization',
            action='get_profile_reporting_details',
            mock_response=response,
        )
        self.mock.instance.register_mock_object(
            service='profile',
            action='get_profiles',
            return_object=[self.profile, manager],
            return_object_path='profiles',
            ids=[self.profile.id, manager.id],
        )

    def test_no_search_results_client_type_required(self):
        with self.assertFieldError('client_type', 'MISSING'):
            self.client.call_action('no_search_results', query='query')

    def test_no_search_results_query_required(self):
        with self.assertFieldError('query', 'MISSING'):
            self.client.call_action('no_search_results', client_type=token_pb2.WEB)

    @mock.patch('notification.actions.boto3')
    def test_no_search_results(self, patched_boto):
        self._setup_mocks()
        self.client.call_action(
            'no_search_results',
            client_type=token_pb2.WEB,
            query='some search query',
            comment='I was trying to find something, but couldn\'t',
        )
        mock_publish = patched_boto.resource().Topic().publish
        self.assertEqual(mock_publish.call_count, 1)
        kwargs = mock_publish.call_args[1]
        self.assertTrue(kwargs['MessageStructure'], 'json')
