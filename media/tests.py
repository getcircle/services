import urllib

from django.conf import settings
from mock import (
    MagicMock,
    patch,
    PropertyMock,
)
from protobufs.services.media.containers import media_pb2
import service.control
import service.settings
from service.transports import (
    local,
    mock,
)

from services.test import (
    fuzzy,
    mocks,
    TestCase,
)


class TestMediaService(TestCase):

    def setUp(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.mock.instance'
        self.client = service.control.Client('media', token='test-token')
        self.client.set_transport(local.instance)

    def tearDown(self):
        service.settings.DEFAULT_TRANSPORT = 'service.transports.local.instance'

    def _mock_get_profile(self, profile_id=None):
        service = 'profile'
        action = 'get_profile'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_profile(
            mock_response.profile,
            image_url='https://%s.s3.amazonaws.com/%s' % (
                settings.AWS_S3_MEDIA_BUCKET,
                urllib.quote_plus('profiles/%s' % (fuzzy.FuzzyUUID().fuzz(),)),
            ),
        )
        if profile_id is not None:
            mock_response.profile.id = profile_id
        mock.instance.register_mock_response(service, action, mock_response, profile_id=profile_id)
        return mock_response.profile

    def _mock_update_profile(self, profile=None):
        service = 'profile'
        action = 'update_profile'
        mock_response = mock.get_mockable_response(service, action)
        mocks.mock_profile(mock_response.profile)
        if profile is not None:
            mock_response.profile.CopyFrom(profile)
        mock.instance.register_mock_response(
            service,
            action,
            mock_response,
            mock_regex_lookup=r'profile:update_profile:.*',
            profile=mock_response.profile,
        )
        return mock_response.profile

    def test_start_image_upload_profile_invalid_key(self):
        with self.assertFieldError('media_key'):
            self.client.call_action(
                'start_image_upload',
                media_type=media_pb2.PROFILE,
                media_key='invalid',
            )

    def test_start_image_upload_profile_does_not_exist(self):
        # mock the get_profile call to return DOES_NOT_EXIST
        profile_id = fuzzy.FuzzyUUID().fuzz()
        action_response = mock.get_mockable_action_response('profile', 'get_profile')
        action_response.result.errors.append('FIELD_ERROR')
        mock.instance.register_mock_response(
            'profile',
            'get_profile',
            action_response,
            is_action_response=True,
            profile_id=profile_id,
        )
        with self.assertFieldError('media_key', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'start_image_upload',
                media_type=media_pb2.PROFILE,
                media_key=profile_id,
            )

    # TODO add tests for failing connections
    @patch('media.utils.S3Connection')
    def test_start_image_upload_profile(self, mock_s3_connection):
        type(
            mock_s3_connection().get_bucket().initiate_multipart_upload()
        ).id = PropertyMock(return_value=fuzzy.FuzzyUUID().fuzz())
        mock_s3_connection().get_bucket().get_location.return_value = 'us-east-1'
        profile_id = fuzzy.FuzzyUUID().fuzz()
        self._mock_get_profile(profile_id)

        response = self.client.call_action(
            'start_image_upload',
            media_type=media_pb2.PROFILE,
            media_key=profile_id,
        )
        self.assertTrue(response.success)
        self.assertTrue(response.result.upload_instructions.upload_id)
        self.assertTrue(response.result.upload_instructions.upload_url.startswith('https'))
        self.assertIn('profiles', response.result.upload_instructions.upload_url)

    @patch('media.utils.S3Connection')
    def test_start_image_upload_team(self, mock_s3_connection):
        type(
            mock_s3_connection().get_bucket().initiate_multipart_upload()
        ).id = PropertyMock(return_value=fuzzy.FuzzyUUID().fuzz())
        mock_s3_connection().get_bucket().get_location.return_value = 'us-east-1'
        team_id = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action(
            'start_image_upload',
            media_type=media_pb2.TEAM,
            media_key=team_id,
        )
        self.assertTrue(response.success)
        self.assertTrue(response.result.upload_instructions.upload_id)
        self.assertTrue(response.result.upload_instructions.upload_url.startswith('https'))
        self.assertIn('teams', response.result.upload_instructions.upload_url)

    @patch('media.utils.S3Connection')
    def test_start_image_upload_location(self, mock_s3_connection):
        type(
            mock_s3_connection().get_bucket().initiate_multipart_upload()
        ).id = PropertyMock(return_value=fuzzy.FuzzyUUID().fuzz())
        mock_s3_connection().get_bucket().get_location.return_value = 'us-west-2'
        location_id = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action(
            'start_image_upload',
            media_type=media_pb2.LOCATION,
            media_key=location_id,
        )
        self.assertTrue(response.success)
        self.assertTrue(response.result.upload_instructions.upload_id)
        self.assertTrue(response.result.upload_instructions.upload_url.startswith('https'))
        self.assertIn('locations', response.result.upload_instructions.upload_url)

    def test_complete_image_upload_profile_invalid_profile_id(self):
        with self.assertFieldError('media_key'):
            self.client.call_action(
                'complete_image_upload',
                media_type=media_pb2.PROFILE,
                media_key='invalid',
                upload_id='fake',
            )

    def test_complete_image_upload_profile_does_not_exist(self):
        # mock the get_profile call to return DOES_NOT_EXIST
        profile_id = fuzzy.FuzzyUUID().fuzz()
        action_response = mock.get_mockable_action_response('profile', 'get_profile')
        action_response.result.errors.append('FIELD_ERROR')
        mock.instance.register_mock_response(
            'profile',
            'get_profile',
            action_response,
            is_action_response=True,
            profile_id=profile_id,
        )
        with self.assertFieldError('media_key', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'complete_image_upload',
                media_type=media_pb2.PROFILE,
                media_key=profile_id,
                upload_id='fake',
            )

    def _mock_complete_image_upload(self, mock_s3_connection, mock_multipart):
        # mock the s3 initiation call
        type(
            mock_s3_connection().get_bucket().initiate_multipart_upload()
        ).id = PropertyMock(return_value=fuzzy.FuzzyUUID().fuzz())
        # mock the multipart complete_upload
        mock_response = MagicMock()
        type(mock_response).location = PropertyMock(
            return_value='https://otterbots-media.s3.amazonaws.com/media-id/%s' % (
                fuzzy.FuzzyUUID().fuzz(),
            )
        )
        mock_multipart().complete_upload.return_value = mock_response

    @patch('media.actions.MultiPartUpload')
    @patch('media.utils.S3Connection')
    def test_complete_image_upload_profile(self, mock_s3_connection, mock_multipart):
        self._mock_complete_image_upload(mock_s3_connection, mock_multipart)
        profile_id = fuzzy.FuzzyUUID().fuzz()
        profile = self._mock_get_profile(profile_id)
        self._mock_update_profile(profile)

        response = self.client.call_action(
            'complete_image_upload',
            media_type=media_pb2.PROFILE,
            media_key=profile_id,
            upload_key='profiles/%s' % (profile_id,),
            upload_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self.assertTrue(response.success)
        self.assertTrue(response.result.media_url.startswith('https'))
