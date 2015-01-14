from boto.auth import S3HmacAuthV4Handler
from boto.provider import Provider
from boto.connection import HTTPRequest


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
