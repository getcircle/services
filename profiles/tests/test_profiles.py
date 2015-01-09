from copy import copy

from protobufs.profile_service_pb2 import ProfileService
import service.control

from services.test import (
    fuzzy,
    TestCase,
)


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

    def _create_organization(self):
        response = self.org_client.call_action(
            'create_organization',
            organization={
                'name': fuzzy.FuzzyText().fuzz(),
                'domain': fuzzy.FuzzyText(suffix='.com').fuzz(),
            },
        )
        self.assertTrue(response.success)
        return response.result.organization

    def _create_address(self, organization=None):
        if not organization:
            organization = self._create_organization()

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
        return response.result.address

    def _create_team_and_owner(self, organization_id, address_id, child_of=None):
        user = self._create_user()
        response = self.org_client.call_action(
            'create_team',
            team={
                'organization_id': organization_id,
                'name': fuzzy.FuzzyText().fuzz(),
                'owner_id': user.id,
            },
            child_of=child_of,
        )
        self.assertTrue(response.success)
        team = response.result.team

        profile_data = copy(self.profile_data)
        profile_data['user_id'] = user.id
        profile_data['organization_id'] = organization_id
        profile_data['address_id'] = address_id
        profile_data['team_id'] = team.id
        profile = self._create_profile(profile_data)
        return team, profile

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

    def test_get_profiles_invalid_organization_id(self):
        response = self.client.call_action(
            'get_profiles',
            organization_id='invalid',
        )
        self._verify_field_error(response, 'organization_id')

    def test_get_profiles_with_organization_id(self):
        profile = self._create_profile(self.profile_data)
        response = self.client.call_action(
            'get_profiles',
            organization_id=profile.organization_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)
        self._verify_containers(profile, response.result.profiles[0])

    def test_get_profiles_invalid_team_id(self):
        response = self.client.call_action(
            'get_profiles',
            team_id='invalid',
        )
        self._verify_field_error(response, 'team_id')

    def test_get_profiles(self):
        profile = self._create_profile(self.profile_data)
        response = self.client.call_action(
            'get_profiles',
            team_id=profile.team_id,
        )
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 1)
        self._verify_containers(profile, response.result.profiles[0])

    def test_get_profile(self):
        expected = self._create_profile(self.profile_data)
        response = self.client.call_action(
            'get_profile',
            profile_id=expected.id,
        )
        self._verify_containers(expected, response.result.profile)

    def test_get_profile_full_name(self):
        profile = self._create_profile(self.profile_data)
        self.assertTrue(profile.full_name)

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
        organization = self._create_organization()

        # create an address
        address = self._create_address(organization=organization)

        # create a team structure
        last_team, _ = self._create_team_and_owner(organization.id, address.id)
        for _ in range(5):
            last_team, _ = self._create_team_and_owner(
                organization.id,
                address.id,
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

        # this has no effect, this just makes validating the container easier
        profile.full_name = 'Michael Hahn'

        response = self.client.call_action('update_profile', profile=profile)
        self._verify_containers(profile, response.result.profile)

    def test_get_direct_reports_invalid_profile_id(self):
        response = self.client.call_action('get_direct_reports', profile_id='invalid')
        self._verify_field_error(response, 'profile_id')

    def test_get_direct_reports_profile_does_not_exist(self):
        response = self.client.call_action(
            'get_direct_reports',
            profile_id=fuzzy.FuzzyUUID().fuzz(),
        )
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_get_peers_invalid_profile_id(self):
        response = self.client.call_action('get_peers', profile_id='invalid')
        self._verify_field_error(response, 'profile_id')

    def test_get_peers_profile_does_not_exist(self):
        response = self.client.call_action('get_peers', profile_id=fuzzy.FuzzyUUID().fuzz())
        self._verify_field_error(response, 'profile_id', 'DOES_NOT_EXIST')

    def test_get_direct_reports_invalid_user_id(self):
        response = self.client.call_action('get_direct_reports', user_id='invalid')
        self._verify_field_error(response, 'user_id')

    def _setup_direct_reports_test(self):
        address = self._create_address()

        # create a parent team and owner
        parent_team, owner = self._create_team_and_owner(address.organization_id, address.id)

        # create teams that children to the parent_team
        for _ in range(3):
            self._create_team_and_owner(
                address.organization_id,
                address.id,
                child_of=parent_team.id,
            )

        # add team members to the owners direct team
        for _ in range(3):
            data = copy(self.profile_data)
            data['address_id'] = address.id
            data['organization_id'] = address.organization_id
            data['team_id'] = parent_team.id
            data['user_id'] = self._create_user().id
            self._create_profile(data)
        return owner

    def test_get_direct_reports(self):
        owner = self._setup_direct_reports_test()
        # direct reports for owner should be equal to the number of teams 1
        # level below as well as anyone directly on his team
        response = self.client.call_action('get_direct_reports', profile_id=owner.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 6)

    def test_get_direct_reports_user_id(self):
        owner = self._setup_direct_reports_test()
        response = self.client.call_action('get_direct_reports', user_id=owner.user_id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 6)

    def test_get_direct_reports_no_direct_reports(self):
        address = self._create_address()
        parent_team, _ = self._create_team_and_owner(address.organization_id, address.id)
        self.profile_data['organization_id'] = address.organization_id
        self.profile_data['address_id'] = address.id
        self.profile_data['team_id'] = parent_team.id
        profile = self._create_profile(self.profile_data)

        response = self.client.call_action('get_direct_reports', profile_id=profile.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)

    def test_get_peers_non_owner(self):
        address = self._create_address()
        parent_team, _ = self._create_team_and_owner(address.organization_id, address.id)

        for _ in range(3):
            data = copy(self.profile_data)
            data['address_id'] = address.id
            data['organization_id'] = address.organization_id
            data['team_id'] = parent_team.id
            data['user_id'] = self._create_user().id
            peer = self._create_profile(data)

        response = self.client.call_action('get_peers', profile_id=peer.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 3)

    def test_get_peers(self):
        address = self._create_address()

        # create a parent team
        parent_team, _ = self._create_team_and_owner(address.organization_id, address.id)

        # create a sub-team we'll use as our test case
        team, _ = self._create_team_and_owner(
            address.organization_id,
            address.id,
            child_of=parent_team.id,
        )

        # create teams that are children of the one above
        for _ in range(3):
            _, peer = self._create_team_and_owner(
                address.organization_id,
                address.id,
                child_of=team.id,
            )

        response = self.client.call_action('get_peers', profile_id=peer.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 3)

    def test_get_peers_ceo(self):
        address = self._create_address()

        # create a root team
        _, owner = self._create_team_and_owner(address.organization_id, address.id)
        response = self.client.call_action('get_peers', profile_id=owner.id)
        self.assertTrue(response.success)
        self.assertEqual(len(response.result.profiles), 0)
