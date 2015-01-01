from copy import copy

from protobufs.profile_service_pb2 import ProfileService
import service.control

from services import fuzzy
from services.test import TestCase


class TestProfiles(TestCase):

    def setUp(self):
        self.client = service.control.Client('profile', token='test-token')
        self.user_client = service.control.Client('user', token='test-token')
        self.org_client = service.control.Client(
            'organization',
            token='test-token',
        )
        self.profile_data = {
            'organization_id': fuzzy.FuzzyUUID().fuzz(),
            'user_id': fuzzy.FuzzyUUID().fuzz(),
            'address_id': fuzzy.FuzzyUUID().fuzz(),
            'title': fuzzy.FuzzyText().fuzz(),
            'first_name': fuzzy.FuzzyText().fuzz(),
            'last_name': fuzzy.FuzzyText().fuzz(),
            'cell_phone': '+19492933322',
            'image_url': fuzzy.FuzzyText().fuzz(),
            'email': fuzzy.FuzzyText(suffix='@example.com').fuzz(),
            'team_id': fuzzy.FuzzyUUID().fuzz(),
        }

    def _create_profile(self, data):
        response = self.client.call_action('create_profile', profile=data)
        self.assertTrue(response.success)
        return response.result.profile

    def _create_user(self):
        response = self.user_client.call_action(
            'create_user',
            email=fuzzy.FuzzyText(suffix='@example.com').fuzz(),
        )
        self.assertTrue(response.success)
        return response.result.user

    def _create_team_and_owner(self, organization, address, child_of=None):
        user = self._create_user()
        response = self.org_client.call_action(
            'create_team',
            team={
                'organization_id': organization.id,
                'name': fuzzy.FuzzyText().fuzz(),
                'owner_id': user.id,
            },
            child_of=child_of,
        )
        self.assertTrue(response.success)
        team = response.result.team

        profile_data = copy(self.profile_data)
        profile_data['user_id'] = user.id
        profile_data['organization_id'] = organization.id
        profile_data['address_id'] = address.id
        profile_data['team_id'] = team.id
        self._create_profile(profile_data)
        return team

    def test_create_profile_invalid_organization_id(self):
        self.profile_data['organization_id'] = 'invalid'
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self._verify_field_error(response, 'profile.organization_id')

    def test_create_profile_invalid_user_id(self):
        self.profile_data['user_id'] = 'invalid'
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self._verify_field_error(response, 'profile.user_id')

    def test_create_profile_invalid_address_id(self):
        self.profile_data['address_id'] = 'invalid'
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self._verify_field_error(response, 'profile.address_id')

    def test_create_profile_invalid_team_id(self):
        self.profile_data['team_id'] = 'invalid'
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self._verify_field_error(response, 'profile.team_id')

    def test_create_profile(self):
        profile = self._create_profile(self.profile_data)
        self._verify_container_matches_data(profile, self.profile_data)

    def test_get_profile(self):
        expected = self._create_profile(self.profile_data)
        response = self.client.call_action(
            'get_profile',
            profile_id=expected.id,
        )
        self._verify_containers(expected, response.result.profile)

    def test_get_profile_invalid_profile_id(self):
        response = self.client.call_action(
            'get_profile',
            profile_id='invalid',
        )
        self._verify_field_error(response, 'profile_id')

    def test_get_profile_does_not_exist(self):
        response = self.client.call_action(
            'get_profile',
            profile_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_get_extended_profile_invalid_profile_id(self):
        response = self.client.call_action(
            'get_extended_profile',
            profile_id='invalid',
        )
        self._verify_field_error(response, 'profile_id')

    def test_get_extended_profile_does_not_exist(self):
        response = self.client.call_action(
            'get_extended_profile',
            profile_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_get_extended_profile(self):
        # create an organization
        response = self.org_client.call_action(
            'create_organization',
            organization={
                'name': 'RHLabs',
                'domain': 'rhlabs.com',
            },
        )
        self.assertTrue(response.success)
        organization = response.result.organization

        # create an address
        address_data = {
            'organization_id': organization.id,
            'address_1': '319 Primrose',
            'city': 'Burlingame',
            'region': 'California',
            'postal_code': '94010',
            'country_code': 'US',
        }
        response = self.org_client.call_action(
            'create_address',
            address=address_data,
        )
        self.assertTrue(response.success)
        address = response.result.address

        # create a team structure
        last_team = self._create_team_and_owner(organization, address)
        for _ in range(5):
            last_team = self._create_team_and_owner(
                organization,
                address,
                child_of=last_team.id,
            )
        team = last_team

        # create a user
        user = self._create_user()

        self.profile_data['user_id'] = user.id
        self.profile_data['organization_id'] = organization.id
        self.profile_data['team_id'] = team.id
        self.profile_data['address_id'] = address.id

        # create the profile
        response = self.client.call_action(
            'create_profile',
            profile=self.profile_data,
        )
        self.assertTrue(response.success)
        profile = response.result.profile

        # create tags
        response = self.client.call_action(
            'create_tags',
            organization_id=organization.id,
            tags=[{'name': 'python'}, {'name': 'mysql'}],
        )
        self.assertTrue(response.success)
        tags = response.result.tags

        # add tags to profile
        tag_ids = [tag.id for tag in tags]
        response = self.client.call_action('add_tags', profile_id=profile.id, tag_ids=tag_ids)
        self.assertTrue(response.success)

        # fetch the manager's profile
        response = self.org_client.call_action(
            'get_team',
            team_id=profile.team_id,
        )
        self.assertTrue(response.success)
        team = response.result.team

        response = self.client.call_action(
            'get_profile',
            user_id=team.owner_id,
        )
        self.assertTrue(response.success)
        manager = response.result.profile

        # fetch the extended profile
        response = self.client.call_action(
            'get_extended_profile',
            profile_id=profile.id,
        )

        self.assertTrue(response.success)
        self._verify_containers(profile, response.result.profile)
        self._verify_containers(address, response.result.address)
        self._verify_containers(manager, response.result.manager)
        self._verify_containers(team, response.result.team)
        self.assertEqual(len(tags), len(response.result.tags))

    def test_update_profile_invalid_profile_id(self):
        self.profile_data['id'] = 'invalid'
        response = self.client.call_action('update_profile', profile=self.profile_data)
        self._verify_field_error(response, 'profile.id')

    def test_update_profile_does_not_exist(self):
        self.profile_data['id'] = fuzzy.FuzzyUUID().fuzz()
        response = self.client.call_action('update_profile', profile=self.profile_data)
        self._verify_field_error(response, 'profile.id', 'DOES_NOT_EXIST')

    def test_update_profile(self):
        original = self._create_profile(self.profile_data)
        profile = ProfileService.Containers.Profile()
        profile.CopyFrom(original)

        profile.first_name = 'Michael'
        profile.last_name = 'Hahn'
        profile.email = 'mwhahn@gmail.com'
        profile.cell_phone = '+19492931122'
        profile.title = 'Engineer'

        response = self.client.call_action('update_profile', profile=profile)
        self._verify_containers(profile, response.result.profile)
