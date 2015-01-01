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


def valid_tag_ids(tag_ids):
    db_ids = models.Tag.objects.filter(pk__in=tag_ids).values_list('pk', flat=True)
    return len(tag_ids) == len(db_ids)


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


class CreateTags(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        objects = [models.Tag.objects.from_protobuf(
            p,
            commit=False,
            organization_id=self.request.organization_id,
        ) for p in self.request.tags]

        tags = models.Tag.objects.bulk_create(objects)
        for tag in tags:
            container = self.response.tags.add()
            tag.to_protobuf(container)


class AddTags(actions.Action):

    type_validators = {
        'profile_id': [validators.is_uuid4],
    }

    field_validators = {
        'profile_id': {
            valid_profile: 'DOES_NOT_EXIST',
        },
        'tag_ids': {
            # XXX we may want a more specific error for which tags don't exist
            valid_tag_ids: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        through_model = models.Profile.tags.through
        objects = [through_model(
            profile_id=self.request.profile_id,
            tag_id=tag_id,
        ) for tag_id in self.request.tag_ids]
        through_model.objects.bulk_create(objects)


class GetTags(actions.Action):

    # XXX should we have field_validators for whether or not organization and profile exist?

    type_validators = {
        'organization_id': [validators.is_uuid4],
        'profile_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.HasField('organization_id'):
            parameters['organization_id'] = self.request.organization_id
        else:
            parameters['profile'] = self.request.profile_id

        tags = models.Tag.objects.filter(**parameters)
        for tag in tags:
            container = self.response.tags.add()
            tag.to_protobuf(container)
