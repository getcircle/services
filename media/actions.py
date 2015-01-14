from django.conf import settings
from protobufs.media_service_pb2 import MediaService
from service import (
    actions,
    validators,
)
import service.control
from boto.s3.connection import (
    S3Connection,
    S3ResponseError,
)
from boto.s3.multipart import MultiPartUpload
import uuid

from . import utils


class StartImageUpload(actions.Action):

    def __init__(self, *args, **kwargs):
        super(StartImageUpload, self).__init__(*args, **kwargs)
        self.profile_client = service.control.Client('profile', token=self.token)

    def _validate_profile_id(self, profile_id):
        if not validators.is_uuid4(profile_id):
            self.note_field_error('key', 'INVALID')

        # XXX FUCK!! really need to do errors
        if not self.is_error():
            response = self.profile_client.call_action('get_profile', profile_id=self.request.key)
            if not response.success:
                self.note_field_error('key', 'DOES_NOT_EXIST')

    def _get_s3_connection(self):
        return S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)

    def _get_media_bucket(self):
        connection = self._get_s3_connection()
        return connection.get_bucket(settings.AWS_S3_MEDIA_BUCKET)

    def _build_media_key(self):
        media_object = self.request.media_object
        key = self.request.key
        if media_object == MediaService.PROFILE:
            return 'profile-%s' % (uuid.UUID(key, version=4).hex)

    def validate(self, *args, **kwargs):
        super(StartImageUpload, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.media_object == MediaService.PROFILE:
                self._validate_profile_id(self.request.key)

    def run(self, *args, **kwargs):
        bucket = self._get_media_bucket()
        media_key = self._build_media_key()
        if not media_key:
            self.note_error('ERROR', ('ERROR', 'unsupported media object'))

        response = bucket.initiate_multipart_upload(media_key)
        self.response.upload_instructions.upload_id = response.id

        path = '/%s' % (media_key,)
        self.response.upload_instructions.upload_url = utils.get_presigned_url(
            path=path,
            method='PUT',
            host='%s.s3.amazonaws.com' % (settings.AWS_S3_MEDIA_BUCKET,),
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            params={'uploadId': response.id, 'partNumber': 1},
        )


class CompleteImageUpload(StartImageUpload):

    def run(self, *args, **kwargs):
        bucket = self._get_media_bucket()
        media_key = self._build_media_key()
        multipart_upload = MultiPartUpload(bucket)
        multipart_upload.id = self.request.upload_id
        multipart_upload.key_name = media_key

        try:
            response = multipart_upload.complete_upload()
        except S3ResponseError as e:
            self.note_error('FAILED', ('FAILED', 'failed to complete upload: %s' % (e,)))
        except TypeError:
            self.note_field_error('upload_id', 'UNKNOWN')
        else:
            self.response.media_url = response.location
