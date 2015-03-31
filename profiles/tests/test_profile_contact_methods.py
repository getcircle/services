from protobufs.profile_service_pb2 import ProfileService
import service.control

from services.test import (
    mocks,
    TestCase,
)

from .. import (
    factories,
    models,
)


class TestProfileContactMethods(TestCase):

    def setUp(self):
        self.client = service.control.Client('profile', token='test-token')

    def test_add_contact_methods(self):
        profile = factories.ProfileFactory.create_protobuf()
        for _ in range(2):
            container = profile.contact_methods.add()
            mocks.mock_contact_method(container, id=None)
        response = self.client.call_action('update_profile', profile=profile)
        self.assertEqual(len(response.result.profile.contact_methods), 2)
        self.assertEqual(models.ContactMethod.objects.filter(profile_id=profile.id).count(), 2)

    def test_update_contact_methods(self):
        contact_methods = []
        for _ in range(2):
            container = mocks.mock_contact_method(id=None, type=ProfileService.EMAIL)
            contact_methods.append(container)
        profile = factories.ProfileFactory.create_protobuf(contact_methods=contact_methods)
        self.assertEqual(
            models.ContactMethod.objects.filter(
                profile_id=profile.id,
                type=ProfileService.EMAIL,
            ).count(),
            2,
        )
        for method in profile.contact_methods:
            method.type = ProfileService.SLACK

        response = self.client.call_action('update_profile', profile=profile)
        for method in response.result.profile.contact_methods:
            self.assertEqual(method.type, ProfileService.SLACK)

        self.assertFalse(
            models.ContactMethod.objects.filter(
                profile_id=profile.id,
                type=ProfileService.EMAIL,
            ).exists()
        )
        self.assertEqual(
            models.ContactMethod.objects.filter(
                profile_id=profile.id,
                type=ProfileService.SLACK,
            ).count(),
            2,
        )
