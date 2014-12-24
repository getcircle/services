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
        action_response, response = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertFalse(action_response.result.success)
        self.assertIn('FIELD_ERROR', action_response.result.errors)

        error = action_response.result.error_details[0]
        self.assertEqual('identity.user_id', error.key)
        self.assertEqual('INVALID', error.detail)

    def test_create_identity_internal(self):
        action_response, response = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertTrue(action_response.result.success)
        self.assertEqual(response.identity.email, self.email)
        self.assertEqual(response.identity.first_name, self.first_name)
        self.assertEqual(response.identity.last_name, self.last_name)
        self.assertEqual(response.identity.phone_number, self.phone_number)
        self.assertEqual(response.identity.user_id, self.user_id)

    # XXX
    @unittest.skip(
        'this raises a TypeError, we should be storing an error on the action'
    )
    def test_create_internal_identity_invalid_data(self):
        self.data['type'] = 'invalid'
        action_response, _ = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertFalse(action_response.result.success)

    def test_unique_identities_based_on_type(self):
        action_response, _ = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertTrue(action_response.result.success)

        action_response, _ = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertFalse(action_response.result.success)
        self.assertIn('DUPLICATE', action_response.result.errors)

    def test_get_identity_internal(self):
        action_response, _ = self.client.call_action(
            'create_identity',
            identity=self.data,
        )
        self.assertTrue(action_response.result.success)

        action_response, response = self.client.call_action(
            'get_identity',
            type=IdentityService.Containers.Identity.INTERNAL,
            key=self.email,
        )
        self.assertTrue(action_response.result.success)
        self.assertEqual(response.identity.email, self.email)

    def test_get_identity_internal_non_existant(self):
        action_response, _ = self.client.call_action(
            'get_identity',
            type=IdentityService.Containers.Identity.INTERNAL,
            key=self.email,
        )
        self.assertFalse(action_response.result.success)
        self.assertIn('DOES_NOT_EXIST', action_response.result.errors)
