from protobufs.services.notification import containers_pb2 as notification_containers
import service.control

from services.test import (
    fuzzy,
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
            token=mocks.mock_token(
                profile_id=self.profile.id,
                organization_id=self.profile.organization_id,
            ),
        )

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
            organization_id=self.profile.organization_id,
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
            organization_id=self.profile.organization_id,
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

    def test_update_preference_preference_required(self):
        with self.assertFieldError('preference', 'MISSING'):
            self.client.call_action('update_preference')

    def test_update_preference_preference_notification_type_id_required(self):
        with self.assertFieldError('preference.notification_type_id', 'MISSING'):
            self.client.call_action('update_preference', preference={'subscribed': False})

    def test_update_preference_preference_subscribed_required(self):
        with self.assertFieldError('preference.subscribed', 'MISSING'):
            self.client.call_action('update_preference', preference={'notification_type_id': 0})

    def test_update_preference_opt_out(self):
        models.NotificationType.objects.all().update(opt_in=False)
        notification_type = models.NotificationType.objects.all()[0]

        response = self.client.call_action(
            'update_preference',
            preference={
                'notification_type_id': notification_type.id,
                'subscribed': False,
            },
        )

        preference = response.result.preference
        self.assertTrue(preference.id)
        self.assertFalse(preference.subscribed)
        self.assertEqual(preference.notification_type_id, notification_type.id)

    def test_update_preference_opt_in_default_in(self):
        models.NotificationType.objects.all().update(opt_in=False)
        notification_type = models.NotificationType.objects.all()[0]

        preference = factories.NotificationPreferenceFactory.create(
            notification_type=notification_type,
            profile_id=self.profile.id,
            organization_id=self.profile.organization_id,
            subscribed=False,
        )
        updated = preference.to_protobuf()
        updated.subscribed = True
        response = self.client.call_action('update_preference', preference=updated)
        self.verify_containers(updated, response.result.preference)

        self.assertTrue(
            models.NotificationPreference.objects.filter(
                id=preference.id,
                subscribed=True,
            ).exists()
        )

    def test_update_preference_does_not_exist(self):
        with self.assertFieldError('preference.id', 'DOES_NOT_EXIST'):
            self.client.call_action(
                'update_preference',
                preference={
                    'id': fuzzy.FuzzyUUID().fuzz(),
                    'notification_type_id': 0,
                    'subscribed': True,
                },
            )

    def test_update_preference_new_ignores_profile_id(self):
        models.NotificationType.objects.all().update(opt_in=False)
        notification_type = models.NotificationType.objects.all()[0]

        response = self.client.call_action(
            'update_preference',
            preference={
                'notification_type_id': notification_type.id,
                'subscribed': False,
                'profile_id': fuzzy.FuzzyUUID().fuzz(),
            },
        )
        self.assertEqualUUID4(response.result.preference.profile_id, self.profile.id)

    def test_update_preference_update_ignores_profile_id(self):
        models.NotificationType.objects.all().update(opt_in=False)
        notification_type = models.NotificationType.objects.all()[0]

        preference = factories.NotificationPreferenceFactory.create(
            notification_type=notification_type,
            profile_id=self.profile.id,
            organization_id=self.profile.organization_id,
            subscribed=False,
        )
        updated = preference.to_protobuf()
        updated.subscribed = True
        updated.profile_id = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action('update_preference', preference=updated)
        self.assertTrue(response.result.preference.profile_id, self.profile.id)
