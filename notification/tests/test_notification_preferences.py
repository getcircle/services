from protobufs.services.notification import containers_pb2 as notification_containers
import service.control

from services.test import (
    mocks,
    TestCase,
)

from .. import (
    factories,
    models,
)


class TestNotificationPreferences(TestCase):

    def setUp(self):
        super(TestNotificationPreferences, self).setUp()
        self.profile = mocks.mock_profile()
        self.client = service.control.Client(
            'notification',
            token=mocks.mock_token(profile_id=self.profile.id),
        )

    def test_get_preferences_channel_required(self):
        with self.assertFieldError('channel', 'MISSING'):
            self.client.call_action('get_preferences')

    def test_get_preferences_default_in(self):
        models.NotificationType.objects.all().update(opt_in=False)
        response = self.client.call_action(
            'get_preferences',
            channel=notification_containers.MOBILE_PUSH,
        )
        preference = response.result.preferences[0]
        self.assertTrue(preference.subscribed)

    def test_get_preferences_default_opt_in(self):
        models.NotificationType.objects.all().update(opt_in=True)
        response = self.client.call_action(
            'get_preferences',
            channel=notification_containers.MOBILE_PUSH,
        )
        preference = response.result.preferences[0]
        self.assertFalse(preference.subscribed)

    def test_get_preferences_opted_out(self):
        models.NotificationType.objects.all().update(opt_in=False)
        notification_type = models.NotificationType.objects.all()[0]

        factories.NotificationPreferenceFactory.create(
            profile_id=self.profile.id,
            notification_type=notification_type,
            subscribed=False,
        )
        response = self.client.call_action(
            'get_preferences',
            channel=notification_containers.MOBILE_PUSH,
        )
        tested = False
        for preference in response.result.preferences:
            if preference.notification_type_id == notification_type.id:
                self.assertFalse(preference.subscribed)
                tested = True
                break
        self.assertTrue(tested)

    def test_get_preferences_opt_in(self):
        models.NotificationType.objects.all().update(opt_in=True)
        notification_type = models.NotificationType.objects.all()[0]

        factories.NotificationPreferenceFactory.create(
            profile_id=self.profile.id,
            notification_type=notification_type,
            subscribed=True,
        )
        response = self.client.call_action(
            'get_preferences',
            channel=notification_containers.MOBILE_PUSH,
        )
        tested = False
        for preference in response.result.preferences:
            if preference.notification_type_id == notification_type.id:
                self.assertTrue(preference.subscribed)
                tested = True
                break
        self.assertTrue(tested)
