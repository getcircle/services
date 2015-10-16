import hashlib
import uuid

import arrow
from django.conf import settings
from protobufs.services.media.containers import media_pb2
from service import (
    actions,
    validators,
)
import service.control
from boto.s3.connection import S3ResponseError
from boto.s3.multipart import MultiPartUpload

from . import utils


class StartImageUpload(actions.Action):

    def __init__(self, *args, **kwargs):
        super(StartImageUpload, self).__init__(*args, **kwargs)
        self.profile_client = service.control.Client('profile', token=self.token)
        self.s3_manager = utils.S3Manager()

    def _validate_profile_id(self, profile_id):
        if not validators.is_uuid4(profile_id):
            raise self.ActionFieldError('media_key', 'INVALID')

        try:
            self.profile_client.call_action('get_profile', profile_id=self.request.media_key)
        except service.control.CallActionError:
            raise self.ActionFieldError('media_key', 'DOES_NOT_EXIST')

    def _get_image_identifier(self, key):
        return hashlib.md5(arrow.utcnow().isoformat() + ':' + key).hexdigest()

    # XXX since these are public buckets right now, maybe we don't want to
    # expose what object it represents?
    def _build_media_key(self):
        media_type = self.request.media_type
        if media_type == media_pb2.PROFILE:
            return 'profiles/%s' % (
                self._get_image_identifier(uuid.UUID(self.request.media_key, version=4).hex),
            )
        elif media_type == media_pb2.TEAM:
            return 'teams/%s' % (
                self._get_image_identifier(uuid.UUID(self.request.media_key, version=4).hex),
            )
        elif media_type == media_pb2.LOCATION:
            return 'locations/%s' % (
                self._get_image_identifier(uuid.UUID(self.request.media_key, version=4).hex),
            )

    def validate(self, *args, **kwargs):
        super(StartImageUpload, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.media_type == media_pb2.PROFILE:
                self._validate_profile_id(self.request.media_key)

    def run(self, *args, **kwargs):
        bucket = self.s3_manager.get_media_bucket()
        media_key = self._build_media_key()
        if not media_key:
            self.note_error('ERROR', ('ERROR', 'unsupported media object'))

        response = bucket.initiate_multipart_upload(
            media_key,
            metadata={'content-type': 'image/png'},
        )
        self.response.upload_instructions.upload_id = response.id
        self.response.upload_instructions.upload_key = media_key

        path = '/%s' % (media_key,)
        self.response.upload_instructions.upload_url = utils.get_presigned_url(
            path=path,
            method='PUT',
            host='%s.s3.amazonaws.com' % (settings.AWS_S3_MEDIA_BUCKET,),
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=bucket.get_location() or 'us-east-1',
            params={'uploadId': response.id, 'partNumber': 1},
        )


class CompleteImageUpload(StartImageUpload):

    def _complete_upload(self):
        multipart_upload = MultiPartUpload(self.bucket)
        multipart_upload.id = self.request.upload_id
        multipart_upload.key_name = self.request.upload_key

        try:
            response = multipart_upload.complete_upload()
        except S3ResponseError as e:
            self.note_error('FAILED', ('FAILED', 'failed to complete upload: %s' % (e,)))
            return
        except TypeError:
            self.note_field_error('upload_id', 'UNKNOWN')
            return
        else:
            self.response.media_url = response.location

    def run(self, *args, **kwargs):
        self.bucket = self.s3_manager.get_media_bucket()
        self._complete_upload()
