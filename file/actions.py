from tempfile import NamedTemporaryFile
import uuid

import boto3
from boto.s3.connection import S3ResponseError
from boto.s3.multipart import MultiPartUpload
from django.conf import settings
from service import (
    actions,
    validators,
)
import service.control
import re
import urllib

from services.mixins import PreRunParseTokenMixin

from . import (
    models,
    utils,
)


def get_client(region_name=None):
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=region_name or settings.AWS_REGION_NAME,
    )


def get_upload_key(file_name):
    clean_file_name = re.sub('\s', '_', file_name.encode('ascii', 'ignore'))
    key = '%s/%s' % (uuid.uuid4().hex, clean_file_name)
    return key


class StartUpload(actions.Action):

    required_fields = ('file_name',)

    def run(self, *args, **kwargs):
        s3_manager = utils.S3Manager()
        bucket = s3_manager.get_bucket()
        upload_key = get_upload_key(self.request.file_name)

        metadata = {}
        if self.request.content_type:
            metadata['content-type'] = self.request.content_type

        response = bucket.initiate_multipart_upload(
            upload_key,
            metadata=metadata,
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

    required_fields = ('upload_key', 'upload_id', 'file_name')

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
            return None, None
        except TypeError:
            self.note_field_error('upload_id', 'UNKNOWN')
            return None, None

        key = bucket.get_key(self.request.upload_key)
        region_name = bucket.get_location() or 'us-east-1'
        return key, region_name

    def run(self, *args, **kwargs):
        s3_file, region_name = self._complete_upload()
        if not s3_file:
            return

        instance = models.File.objects.create(
            by_profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            name=self.request.file_name,
            content_type=s3_file.content_type,
            size=s3_file.size,
            key=self.request.upload_key,
            region_name=region_name,
        )
        instance.to_protobuf(self.response.file, token=self.token)


class GetFiles(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'ids': [validators.is_uuid4_list],
    }
    required_fields = ('ids',)

    def run(self, *args, **kwargs):
        files = models.File.objects.filter(
            organization_id=self.parsed_token.organization_id,
            id__in=self.request.ids,
        )
        organization = service.control.get_object(
            service='organization',
            action='get_organization',
            client_kwargs={'token': self.token},
            return_object='organization',
        )
        self.paginated_response(
            self.response.files,
            files,
            lambda item, container: item.to_protobuf(container.add(), organization=organization),
        )


class Delete(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'ids': [validators.is_uuid4_list],
    }
    required_fields = ('ids',)

    def run(self, *args, **kwargs):
        files = models.File.objects.filter(
            organization_id=self.parsed_token.organization_id,
            pk__in=self.request.ids,
        )
        if not files:
            raise self.ActionFieldError('ids', 'DO_NOT_EXIST')
        else:
            files.delete()


class Upload(PreRunParseTokenMixin, actions.Action):

    required_fields = ('file', 'file.name', 'file.bytes')

    def run(self, *args, **kwargs):
        client = get_client()
        upload_key = uuid.uuid4().hex
        get_upload_key(self.request.file.name)
        response = client.put_object(
            Bucket=settings.AWS_S3_FILE_BUCKET,
            Body=self.request.file.bytes,
            ContentType=self.request.file.content_type,
            Key=upload_key,
        )
        try:
            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code != 200:
                raise self.ActionError(
                    'UPLOAD_ERROR',
                    ('UPLOAD_ERROR', 'HTTPStatusCode: %s' % (status_code,)),
                )
        except KeyError:
            raise self.ActionError('UPLOAD_ERROR')

        instance = models.File.objects.create(
            by_profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
            name=self.request.file.name,
            content_type=self.request.file.content_type,
            size=len(self.request.file.bytes),
            key=upload_key,
        )
        instance.to_protobuf(self.response.file, token=self.token)


class GetFile(PreRunParseTokenMixin, actions.Action):

    required_fields = ('id',)
    type_validators = {
        'id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            instance = models.File.objects.get(
                pk=self.request.id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.File.DoesNotExist:
            raise self.ActionFieldError('id', 'DOES_NOT_EXIST')

        instance.to_protobuf(self.response.file, token=self.token)
        with NamedTemporaryFile() as dest:
            client = get_client(instance.region_name)
            client.download_file(Bucket=instance.bucket, Key=instance.key, Filename=dest.name)
            with open(dest.name, 'r') as proxy:
                self.response.file.bytes = proxy.read()
