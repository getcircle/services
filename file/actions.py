import uuid

from boto.s3.connection import S3ResponseError
from boto.s3.multipart import MultiPartUpload
from django.conf import settings
from service import actions

from services.mixins import PreRunParseTokenMixin

from . import (
    models,
    utils,
)


class StartUpload(actions.Action):

    required_fields = ('file_name', 'content_type')

    def run(self, *args, **kwargs):
        s3_manager = utils.S3Manager()
        bucket = s3_manager.get_bucket()
        upload_key = '%s/%s' % (uuid.uuid4().hex, self.request.file_name)

        response = bucket.initiate_multipart_upload(
            upload_key,
            metadata={'content-type': self.request.content_type},
        )
        self.response.upload_instructions.upload_id = response.id
        self.response.upload_instructions.upload_key = upload_key

        region_name = bucket.get_location() or 'us-east-1'
        if region_name != 'us-east-1':
            host = '%s.s3-%s.amazonaws.com' % (settings.AWS_S3_FILE_BUCKET, region_name)
        else:
            host = '%s.s3.amazonaws.com' % (settings.AWS_S3_FILE_BUCKET,)

        path = '/%s' % (upload_key,)
        self.response.upload_instructions.upload_url = utils.get_presigned_url(
            path=path,
            method='PUT',
            host=host,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=bucket.get_location() or 'us-east-1',
            params={'uploadId': response.id, 'partNumber': 1},
        )


class CompleteUpload(PreRunParseTokenMixin, actions.Action):

    required_fields = ('upload_key', 'upload_id')

    def _complete_upload(self):
        s3_manager = utils.S3Manager()
        bucket = s3_manager.get_bucket()

        multipart_upload = MultiPartUpload(bucket)
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
            return response.location

    def run(self, *args, **kwargs):
        source_url = self._complete_upload()
        if not source_url:
            return

        instance = models.File.objects.create(
            by_profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            source_url=source_url,
        )
        instance.to_protobuf(self.response.file)