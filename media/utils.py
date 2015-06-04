from boto.auth import S3HmacAuthV4Handler
from boto.connection import HTTPRequest
from boto.provider import Provider
from boto.s3.connection import S3Connection

from django.conf import settings


def get_presigned_url(
        path,
        method,
        host,
        access_key,
        secret_key,
        protocol='https',
        expires=None,
        params=None,
        headers=None,
    ):
    if protocol == 'https':
        port = 443
    else:
        port = 80

    if expires is None:
        expires = 60 * 5

    params = params or {}
    headers = headers or {}
    request = HTTPRequest(
        method=method,
        protocol=protocol,
        host=host,
        port=port,
        path=path,
        auth_path=None,
        params=params,
        headers=headers,
        body='',
    )
    provider = Provider('aws', access_key=access_key, secret_key=secret_key)
    auth = S3HmacAuthV4Handler(
        host=host,
        config=None,
        provider=provider,
    )
    return auth.presign(request, expires)


class S3Manager(object):

    def get_connection(self):
        if not hasattr(self, '_s3_connection'):
            self._s3_connection = S3Connection(
                settings.AWS_ACCESS_KEY_ID,
                settings.AWS_SECRET_ACCESS_KEY,
            )
        return self._s3_connection

    def get_media_bucket(self, media_bucket=None):
        media_bucket = media_bucket or settings.AWS_S3_MEDIA_BUCKET
        connection = self.get_connection()
        return connection.get_bucket(media_bucket)
