import json

import arrow
import boto3
from django.conf import settings
from protobufs.services.notification import containers_pb2 as notification_containers
from protobufs.services.user.containers import token_pb2
from service import actions
import service.control

from services import mixins
from services.utils import build_slack_message

from . import (
    models,
    platforms,
    providers,
)


class GetPreferences(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = ('channel',)

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.channel == notification_containers.MOBILE_PUSH:
            parameters = {'channels': models.NotificationType.channels.mobile_push}

        notification_types = models.NotificationType.objects.filter(**parameters)
        preferences = models.NotificationPreference.objects.filter(
            profile_id=self.parsed_token.profile_id,
            organization_id=self.parsed_token.organization_id,
        )
        notification_type_to_preference = dict((preference.notification_type_id, preference) for
                                               preference in preferences)
        # TODO paginate this
        for notification_type in notification_types:
            preference = notification_type_to_preference.get(notification_type.id)
            container = notification_type.to_protobuf()

            subscribed = not container.opt_in
            if preference:
                subscribed = preference.subscribed

            self.response.preferences.add(
                profile_id=self.parsed_token.profile_id,
                notification_type_id=container.id,
                subscribed=subscribed,
                notification_type=container,
            )


class UpdatePreference(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'preference',
        'preference.notification_type_id',
        'preference.subscribed',
    )

    def run(self, *args, **kwargs):
        if not self.request.preference.id:
            preference = models.NotificationPreference.objects.from_protobuf(
                self.request.preference,
                profile_id=self.parsed_token.profile_id,
                organization_id=self.parsed_token.organization_id,
            )
        else:
            try:
                preference = models.NotificationPreference.objects.get(
                    pk=self.request.preference.id,
                )
            except models.NotificationPreference.DoesNotExist:
                raise self.ActionFieldError('preference.id', 'DOES_NOT_EXIST')

            preference.update_from_protobuf(self.request.preference)
            preference.save()

        preference.to_protobuf(self.response.preference)


class RegisterDevice(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'device',
        'device.id',
        'device.notification_token',
        'device.provider',
    )

    def _register_token(self, provider, provider_platform):
        try:
            provider_token = provider.register_notification_token(
                token=self.request.device.notification_token,
                platform=provider_platform,
                user_id=self.parsed_token.user_id,
            )
        except providers.exceptions.TokenAlreadyRegistered:
            # if a notification token exists for this device_id, delete it
            # XXX should be logging whats happening here
            try:
                token = models.NotificationToken.objects.get(device_id=self.request.device.id)
                provider.delete_token(token.provider_token)
                token.delete()
            except models.NotificationToken.DoesNotExist:
                raise

            provider_token = provider.register_notification_token(
                token=self.request.device.notification_token,
                platform=provider_platform,
                user_id=self.parsed_token.user_id,
            )
        return provider_token

    def run(self, *args, **kwargs):
        provider = providers.SNS()
        provider_platform = provider.get_platform_for_device(self.request.device)
        try:
            notification_token = models.NotificationToken.objects.get(
                device_id=self.request.device.id,
                user_id=self.parsed_token.user_id,
                provider=provider.provider,
                provider_platform=provider_platform,
            )
        except models.NotificationToken.DoesNotExist:
            provider_token = self._register_token(provider, provider_platform)
            notification_token = models.NotificationToken.objects.create(
                user_id=self.parsed_token.user_id,
                device_id=self.request.device.id,
                provider_token=provider_token,
                provider=provider.provider,
                provider_platform=provider_platform,
            )

        notification_token.to_protobuf(self.response.notification_token)


class SendNotification(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'notification',
        'notification.notification_type_id',
    )

    def validate(self, *args, **kwargs):
        super(SendNotification, self).validate(*args, **kwargs)
        if not self.is_error():
            if not any([self.request.HasField('to_profile_id'), self.request.to_profile_ids]):
                raise self.ActionError(
                    'MISSING_RECIPIENTS',
                    (
                        'MISSING_RECIPIENTS',
                        'must specify one of ("to_profile_id", "to_profile_ids"',
                    ),
                )

    def _send_notification(self, to_profile_id, notification_type, notification_preference):
        if notification_type.opt_in and not notification_preference:
            raise self.ActionFieldError('notification.notification_type_id', 'NOT_OPTED_IN')
        elif notification_preference and not notification_preference.subscribed:
            raise self.ActionFieldError('notification.notification_type_id', 'UNSUBSCRIBED')

        profile = service.control.get_object(
            service='profile',
            action='get_profile',
            return_object='profile',
            client_kwargs={'token': self.token},
            profile_id=to_profile_id,
        )
        devices = service.control.get_object(
            service='user',
            action='get_active_devices',
            return_object='devices',
            client_kwargs={'token': self.token},
            user_id=profile.user_id,
        )

        # XXX should support indexing these properly
        if not devices:
            raise self.ActionFieldError('to_profile_id', 'NO_ACTIVE_DEVICES')

        notification_tokens = models.NotificationToken.objects.filter(
            user_id=profile.user_id,
            device_id__in=[device.id for device in devices],
        )

        if not notification_tokens:
            raise self.ActionFieldError('to_profile_id', 'NO_NOTIFICATION_TOKENS')

        for notification_token in notification_tokens:
            provider = providers.SNS()
            provider_platform = notification_token.provider_platform
            if provider_platform == notification_containers.NotificationTokenV1.APNS:
                platform = platforms.APNS(service_token=self.token)
            elif provider_platform == notification_containers.NotificationTokenV1.GCM:
                platform = platforms.GCM(service_token=self.token)
            else:
                raise self.ActionError(
                    'UNSUPPORTED_PLATFORM',
                    (
                        'UNSUPPORTED_PLATFORM',
                        'Unsupported notification platform: %s' % (provider_platform,),
                    ),
                )

            message = platform.construct_message(
                to_profile_id,
                self.request.notification,
            )
            provider.publish_notification(message, notification_token.provider_token)

    def run(self, *args, **kwargs):
        if self.request.to_profile_id:
            to_profile_ids = [self.request.to_profile_id]
        else:
            to_profile_ids = self.request.to_profile_ids

        notification_type = models.NotificationType.objects.get(
            pk=self.request.notification.notification_type_id,
        )
        preferences = models.NotificationPreference.objects.filter(
            profile_id__in=to_profile_ids,
            notification_type=notification_type,
            organization_id=self.parsed_token.organization_id,
        )
        preferences_dict = dict(
            (str(preference.profile_id), preference) for preference in preferences
        )
        for to_profile_id in to_profile_ids:
            self._send_notification(
                to_profile_id,
                notification_type,
                preferences_dict.get(to_profile_id),
            )


class NoSearchResults(mixins.PreRunParseTokenMixin, actions.Action):

    required_fields = ('client_type', 'query')

    def _get_profile_and_manager(self):
        response = service.control.call_action(
            service='organization',
            action='get_profile_reporting_details',
            client_kwargs={'token': self.token},
        )
        reporting_details = response.result

        profile_ids = [self.parsed_token.profile_id]
        if reporting_details.manager_profile_id:
            profile_ids.append(reporting_details.manager_profile_id)

        response = service.control.call_action(
            service='profile',
            action='get_profiles',
            client_kwargs={'token': self.token},
            ids=profile_ids,
        )
        profile_dict = dict((p.id, p) for p in response.result.profiles)
        manager = profile_dict.get(reporting_details.manager_profile_id)
        profile = profile_dict.get(self.parsed_token.profile_id)
        return profile, manager

    def _get_client_type(self):
        return dict(zip(token_pb2.ClientTypeV1.values(), token_pb2.ClientTypeV1.keys()))[
            self.request.client_type
        ]

    def _get_email_message(self, organization, profile, manager):
        parameters = {
            'company': organization.name,
            'name': profile.full_name,
            'title': profile.display_title,
            'query': self.request.query,
            'client_type': self._get_client_type(),
            'joined': '',
            'comment': '',
            'manager': '',
        }
        if profile.hire_date:
            joined = arrow.get(profile.hire_date).humanize()
            parameters['joined'] = 'Joined company: %s\n' % (joined,)

        if self.request.comment:
            parameters['comment'] = 'Question:\n %s' % (self.request.comment,)

        if manager:
            parameters['manager'] = 'Manager: %s, %s\n' % (
                manager.full_name,
                manager.display_title,
            )

        return (
            'Company: %(company)s\n'
            'Name: %(name)s, %(title)s\n'
            '%(manager)s\n'
            '%(joined)s'
            'App: %(client_type)s\n'
            '\nSearch Query: %(query)s\n'
            '%(comment)s'
        ) % parameters

    def _get_lambda_message(self, organization, profile, manager):
        fields = [
            {
                'title': 'Company',
                'value': organization.domain,
                'short': False,
            },
            {
                'title': 'Profile',
                'value': '%s, %s' % (profile.full_name, profile.display_title),
                'short': False,
            },
        ]
        if manager:
            fields.append({
                'title': 'Manager',
                'value': '%s, %s' % (manager.full_name, manager.display_title),
                'short': False,
            })

        if profile.hire_date:
            fields.append({
                'title': 'Joined company',
                'value': arrow.get(profile.hire_date).humanize(),
                'short': False,
            })

        fields.extend([
            {
                'title': 'App',
                'value': self._get_client_type(),
                'short': False,
            },
            {
                'title': 'Search Query',
                'value': self.request.query,
                'short': False,
            },
        ])

        if self.request.comment:
            fields.append({
                'title': 'Question',
                'value': self.request.comment,
                'short': False,
            })

        attachments = [
            {
                'fallback': '[%s] No Search Results. "%s"' % (
                    organization.domain,
                    self.request.query,
                ),
                'pretext': '[%s] No Search Results' % (organization.domain,),
                'fields': fields,
            }
        ]
        return build_slack_message(attachments, '#no-search-results')

    def _send_notification(self, organization, profile, manager):
        sns = boto3.resource('sns', **settings.AWS_SNS_KWARGS)
        topic = sns.Topic(settings.AWS_SNS_TOPIC_NO_SEARCH_RESULTS)
        topic.publish(
            Subject='[%s] No Search Results' % (organization.domain,),
            Message=json.dumps({
                'default': self._get_email_message(organization, profile, manager),
                'lambda': self._get_lambda_message(organization, profile, manager),
            }),
            MessageStructure='json',
        )

    def run(self, *args, **kwargs):
        organization = service.control.get_object(
            service='organization',
            action='get_organization',
            client_kwargs={'token': self.token},
            return_object='organization',
        )
        profile, manager = self._get_profile_and_manager()
        self._send_notification(organization, profile, manager)
