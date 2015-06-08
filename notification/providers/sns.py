import json

import boto
from django.conf import settings
from protobufs.services.notification import containers_pb2 as notification_containers
from protobufs.services.user import containers_pb2 as user_containers

from . import exceptions


PLATFORM_APPLICATION_MAP = {
    notification_containers.NotificationTokenV1.APNS: settings.AWS_SNS_PLATFORM_APPLICATION_APNS,
    notification_containers.NotificationTokenV1.GCM: settings.AWS_SNS_PLATFORM_APPLICATION_GCM,
}


class Provider(object):

    provider = notification_containers.NotificationTokenV1.SNS

    def _get_platform_from_arn(self, arn):
        parts = arn.split('/', 1)
        endpoint_parts = parts[1].split('/')
        return endpoint_parts[0]

    @property
    def sns_connection(self):
        if not hasattr(self, '_sns_connection'):
            self._sns_connection = boto.connect_sns(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        return self._sns_connection

    def register_notification_token(self, token, platform, user_id):
        try:
            platform_application_arn = PLATFORM_APPLICATION_MAP[platform]
        except KeyError:
            raise exceptions.UnsupportedPlatform(platform)

        # XXX catch the BotoServerError
        response = self.sns_connection.create_platform_endpoint(
            platform_application_arn=platform_application_arn,
            token=token,
            custom_user_data=json.dumps({'user_id': user_id}),
        )
        try:
            return response[
                'CreatePlatformEndpointResponse'
            ]['CreatePlatformEndpointResult']['EndpointArn']
        except KeyError:
            raise exceptions.ProviderError()

    def get_platform_for_device(self, device):
        platform = None
        if device.provider == user_containers.DeviceV1.APPLE:
            platform = notification_containers.NotificationTokenV1.APNS
        else:
            raise exceptions.UnsupportedProvider(device.provider)
        return platform

    def publish_notification(self, message, provider_token, is_json=True, **kwargs):
        parameters = {}
        if is_json:
            parameters['message_structure'] = 'json'

        platform = self._get_platform_from_arn(provider_token)
        response = self.sns_connection.publish(
            message=json.dumps({platform: message}),
            target_arn=provider_token,
            **parameters
        )
        return response
