from protobufs.services.profile import containers_pb2 as profile_containers
import service.control

from services.test import (
    mocks,
    MockedTestCase,
)

from .. import (
    factories,
    models,
)


class TestProfileContactMethods(MockedTestCase):

    def setUp(self):
        super(TestProfileContactMethods, self).setUp()
        self.organization = mocks.mock_organization()
        self.client = service.control.Client(
            'profile',
            token=mocks.mock_token(organization_id=self.organization.id),
        )
        self.mock.instance.dont_mock_service('profile')

    def test_add_contact_methods(self):
        profile = factories.ProfileFactory.create_protobuf(organization_id=self.organization.id)
        for _ in range(2):
            container = profile.contact_methods.add()
            mocks.mock_contact_method(container, id=None)
        response = self.client.call_action('update_profile', profile=profile)
        self.assertEqual(len(response.result.profile.contact_methods), 2)
        self.assertEqual(models.ContactMethod.objects.filter(profile_id=profile.id).count(), 2)

    def test_update_contact_methods(self):
        contact_methods = []
        for _ in range(2):
            container = mocks.mock_contact_method(
                id=None,
                contact_method_type=profile_containers.ContactMethodV1.EMAIL,
            )
            contact_methods.append(container)
        profile = factories.ProfileFactory.create_protobuf(
            contact_methods=contact_methods,
            organization_id=self.organization.id,
        )
        self.assertEqual(
            models.ContactMethod.objects.filter(
                profile_id=profile.id,
                type=profile_containers.ContactMethodV1.EMAIL,
            ).count(),
            2,
        )
        for method in profile.contact_methods:
            method.contact_method_type = profile_containers.ContactMethodV1.SLACK

        response = self.client.call_action('update_profile', profile=profile)
        for method in response.result.profile.contact_methods:
            self.assertEqual(method.contact_method_type, profile_containers.ContactMethodV1.SLACK)

        self.assertFalse(
            models.ContactMethod.objects.filter(
                profile_id=profile.id,
                type=profile_containers.ContactMethodV1.EMAIL,
            ).exists()
        )
        self.assertEqual(
            models.ContactMethod.objects.filter(
                profile_id=profile.id,
                type=profile_containers.ContactMethodV1.SLACK,
            ).count(),
            2,
        )

    def test_delete_contact_methods(self):
        # create contact methods for separate profile
        factories.ProfileFactory.create_protobuf(
            contact_methods=[mocks.mock_contact_method(id=None) for _ in range(5)],
            organization_id=self.organization.id,
        )
        contact_methods = [mocks.mock_contact_method(id=None) for _ in range(3)]
        profile = factories.ProfileFactory.create_protobuf(
            contact_methods=contact_methods,
            organization_id=self.organization.id,
        )
        # remove one of the contact methods
        removed_contact_method = profile.contact_methods[2]
        preserved_contact_methods = list(profile.contact_methods[:2])
        profile.ClearField('contact_methods')
        profile.contact_methods.extend(preserved_contact_methods)

        response = self.client.call_action('update_profile', profile=profile)
        self.assertEqual(len(response.result.profile.contact_methods), 2)
        self.assertEqual(models.ContactMethod.objects.all().count(), 7)
        self.assertFalse(
            models.ContactMethod.objects.filter(id=removed_contact_method.id).exists(),
        )

    def test_delete_all_contact_methods(self):
        contact_methods = [mocks.mock_contact_method(id=None) for _ in range(3)]
        profile = factories.ProfileFactory.create_protobuf(
            contact_methods=contact_methods,
            organization_id=self.organization.id,
        )
        # remove all contact methods
        profile.ClearField('contact_methods')

        response = self.client.call_action('update_profile', profile=profile)
        self.assertEqual(len(response.result.profile.contact_methods), 0)
        self.assertEqual(models.ContactMethod.objects.all().count(), 0)
