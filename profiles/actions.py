import service.control
from service import (
    actions,
    validators,
)

from . import (
    models,
)


def valid_profile(profile_id):
    return models.Profile.objects.filter(pk=profile_id).exists()


def valid_profile_with_user_id(user_id):
    return models.Profile.objects.filter(user_id=user_id).exists()


class CreateProfile(actions.Action):

    type_validators = {
        'profile.address_id': [validators.is_uuid4],
        'profile.organization_id': [validators.is_uuid4],
        'profile.team_id': [validators.is_uuid4],
        'profile.user_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        profile = models.Profile.objects.from_protobuf(
            self.request.profile,
        )
        profile.to_protobuf(self.response.profile)


class GetProfile(actions.Action):
    # XXX add some concept of "oneof"

    type_validators = {
        'user_id': [validators.is_uuid4],
        'profile_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
        'user_id': {
            valid_profile_with_user_id: 'DOES_NOT_EXIST',
        },
    }

    def validate(self, *args, **kwargs):
        super(GetProfile, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.WhichOneof('lookup_key') is None:
                self.note_error(
                    'INVALID',
                    ('MISSING', '`user_id` or `profile_id` must be provided'),
                )

    def _get_profile(self):
        parameters = {}
        if self.request.profile_id:
            parameters['pk'] = self.request.profile_id
        else:
            parameters['user_id'] = self.request.user_id

        return models.Profile.objects.get(**parameters)

    def run(self, *args, **kwargs):
        profile = self._get_profile()
        profile.to_protobuf(self.response.profile)


class GetExtendedProfile(GetProfile):

    @property
    def organization_client(self):
        if not hasattr(self, '_organization_client'):
            self._organization_client = service.control.Client(
                'organization',
                token=self.token,
            )
        return self._organization_client

    def _fetch_address(self, address_id):
        # TODO this should raise an error if it doesn't succeed
        response = self.organization_client.call_action(
            'get_address',
            address_id=address_id,
        )
        return response.result.address

    def _fetch_team(self, team_id):
        # TODO this should raise an error if it doesn't succeed
        response = self.organization_client.call_action(
            'get_team',
            team_id=team_id,
        )
        return response.result.team

    def _get_manager(self, manager_id):
        return models.Profile.objects.get(user_id=manager_id)

    def run(self, *args, **kwargs):
        profile = self._get_profile()
        profile = models.Profile.objects.get(pk=self.request.profile_id)
        profile.to_protobuf(self.response.profile)

        address = self._fetch_address(str(profile.address_id))
        self.response.address.CopyFrom(address)

        team = self._fetch_team(str(profile.team_id))
        self.response.team.CopyFrom(team)

        manager = self._get_manager(team.owner_id)
        manager.to_protobuf(self.response.manager)
