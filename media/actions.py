import hashlib
import urllib
import uuid

import arrow
from django.conf import settings
from protobufs.media_service_pb2 import MediaService
from protobufs.profile_service_pb2 import ProfileService
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

from . import utils


class StartImageUpload(actions.Action):

    def __init__(self, *args, **kwargs):
        super(StartImageUpload, self).__init__(*args, **kwargs)
        self.profile_client = service.control.Client('profile', token=self.token)

    def _validate_profile_id(self, profile_id):
        if not validators.is_uuid4(profile_id):
            self.note_field_error('media_key', 'INVALID')

        # XXX FUCK!! really need to do errors
        if not self.is_error():
            response = self.profile_client.call_action(
                'get_profile',
                profile_id=self.request.media_key,
            )
            if not response.success:
                self.note_field_error('media_key', 'DOES_NOT_EXIST')

    def _get_s3_connection(self):
        return S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)

    def _get_media_bucket(self):
        connection = self._get_s3_connection()
        return connection.get_bucket(settings.AWS_S3_MEDIA_BUCKET)

    def _get_image_identifier(self, key):
        return hashlib.md5(arrow.utcnow().isoformat() + ':' + key).hexdigest()

    def _build_media_key(self):
        media_object = self.request.media_object
        if media_object == MediaService.PROFILE:
            return 'profiles/%s' % (
                self._get_image_identifier(uuid.UUID(self.request.media_key, version=4).hex),
            )

    def validate(self, *args, **kwargs):
        super(StartImageUpload, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.media_object == MediaService.PROFILE:
                self._validate_profile_id(self.request.media_key)

    def run(self, *args, **kwargs):
        bucket = self._get_media_bucket()
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

    def _delete_previous_profile_image(self):
        client = service.control.Client('profile', token=self.token)
        response = client.call_action('get_profile', profile_id=self.request.media_key)
        if not response.success:
            print 'warning: failed to fetch profile'
            return

        old_image_url = response.result.profile.image_url
        # update the profile with the new image and delete the previous image
        # (we only do this if the update succeeds)
        updated_profile = ProfileService.Containers.Profile()
        updated_profile.CopyFrom(response.result.profile)
        updated_profile.image_url = self.response.media_url
        response = client.call_action('update_profile', profile=updated_profile)
        # XXX should we rollback the image upload if this happens?
        if not response.success:
            print 'warning: failed to fetch profile'
            return
        else:
            if old_image_url:
                unquoted_key = urllib.unquote_plus(old_image_url)
                key_parts = unquoted_key.rsplit('/')[-2:]
                key_name = '/'.join(key_parts)
                self.bucket.delete_key(key_name)

    def _delete_previous_image(self):
        if self.request.media_object == MediaService.PROFILE:
            self._delete_previous_profile_image()

    def run(self, *args, **kwargs):
        self.bucket = self._get_media_bucket()
        self._complete_upload()
        if not self.is_error():
            self._delete_previous_image()