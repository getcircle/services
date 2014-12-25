import unittest
import uuid
from django.test import TestCase
import service.control

from protobufs.identity_service_pb2 import IdentityService


class TestIdentityActions(TestCase):

    def setUp(self):
        self.user_id = uuid.uuid4().hex
        self.first_name = 'Michael'
        self.last_name = 'Hahn'
        self.email = 'mwhahn@gmail.com'
        self.phone_number = '+19492933322'
        self.data = {
            'user_id': self.user_id,
            'type': IdentityService.Containers.Identity.INTERNAL,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone_number': self.phone_number,
        }

        self.client = service.control.Client('identity', token='test-token')

    def test_create_identity_invalid_user_id(self):
        self.data['user_id'] = 'invalid'
        response = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertFalse(response.success)
        self.assertIn('FIELD_ERROR', response.errors)

        error = response.error_details[0]
        self.assertEqual('identity.user_id', error.key)
        self.assertEqual('INVALID', error.detail)

    def test_create_identity_internal(self):
        response = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertTrue(response.success)
        self.assertEqual(response.result.identity.email, self.email)
        self.assertEqual(response.result.identity.first_name, self.first_name)
        self.assertEqual(response.result.identity.last_name, self.last_name)
        self.assertEqual(
            response.result.identity.phone_number,
            self.phone_number,
        )
        self.assertEqual(response.result.identity.user_id, self.user_id)

    # XXX
    @unittest.skip(
        'this raises a TypeError, we should be storing an error on the action'
    )
    def test_create_internal_identity_invalid_data(self):
        self.data['type'] = 'invalid'
        response = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertFalse(response.success)

    def test_unique_identities_based_on_type(self):
        response = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertTrue(response.success)

        response = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertFalse(response.success)
        self.assertIn('DUPLICATE', response.errors)

    def test_get_identity_internal(self):
        response = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertTrue(response.success)

        response = self.client.call_action(
            'get_identity',
            type=IdentityService.Containers.Identity.INTERNAL,
            key=self.email,
        )
        self.assertTrue(response.success)
        self.assertEqual(response.result.identity.email, self.email)

    def test_get_identity_internal_non_existant(self):
        response = self.client.call_action(
            'get_identity',
            type=IdentityService.Containers.Identity.INTERNAL,
            key=self.email,
        )
        self.assertFalse(response.success)
        self.assertIn('DOES_NOT_EXIST', response.errors)
