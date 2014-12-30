import uuid
import django.db
from service import (
    actions,
    validators,
)

from . import models


def valid_organization(organization_id):
    return models.Organization.objects.filter(pk=organization_id).exists()


def valid_team(team_id):
    return models.Team.objects.filter(pk=team_id).exists()


def valid_address(address_id):
    return models.Address.objects.filter(pk=address_id).exists()


class CreateOrganization(actions.Action):

    def _create_organization(self):
        organization = None
        try:
            organization = models.Organization.objects.from_protobuf(
                self.request.organization,
            )
        except django.db.IntegrityError:
            self.note_error(
                'FIELD_ERROR',
                ('organization.domain', 'DUPLICATE'),
            )
        return organization

    def run(self, *args, **kwargs):
        model = self._create_organization()
        if model:
            model.to_protobuf(self.response.organization)


class CreateTeam(actions.Action):

    type_validators = {
        'team.owner_id': [validators.is_uuid4],
        'team.organization_id': [validators.is_uuid4],
        'child_of': [validators.is_uuid4],
    }

    field_validators = {
        'team.organization_id': {
            valid_organization: 'DOES_NOT_EXIST',
        }
    }

    def _get_parent_team(self):
        if not self.request.child_of:
            return None

        if not hasattr(self, '_parent_team'):
            self._parent_team = models.Team.objects.get_or_none(
                pk=self.request.child_of,
            )
        return self._parent_team

    def validate(self, *args, **kwargs):
        super(CreateTeam, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.child_of:
                parent_team = self._get_parent_team()
                if (
                    parent_team is None or
                    str(parent_team.organization_id) != self.request.team.organization_id
                ):
                    self.note_field_error('child_of', 'DOES_NOT_EXIST')

    def _resolve_path(self, team_id):
        if not self.request.child_of:
            return team_id

        parent_team = self._get_parent_team()
        return parent_team.path + '.' + team_id

    def _create_team(self):
        team_id = uuid.uuid4()
        path = self._resolve_path(team_id.hex)
        return models.Team.objects.from_protobuf(
            self.request.team,
            id=team_id,
            path=path,
        )

    def run(self, *args, **kwargs):
        team = self._create_team()
        team.to_protobuf(self.response.team, path=team.get_path())


class GetTeam(actions.Action):

    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    field_validators = {
        'team_id': {
            valid_team: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        team = models.Team.objects.get(pk=self.request.team_id)
        team.to_protobuf(self.response.team, path=team.get_path())


class CreateAddress(actions.Action):

    type_validators = {
        'address.organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        address = models.Address.objects.from_protobuf(
            self.request.address,
        )
        address.to_protobuf(self.response.address)


class DeleteAddress(actions.Action):

    type_validators = {
        'address_id': [validators.is_uuid4],
    }

    field_validators = {
        'address_id': {
            valid_address: 'DOES_NOT_EXIST',
        }
    }

    def run(self, *args, **kwargs):
        # XXX should we prevent this since people may have profiles associated
        # with it?
        models.Address.objects.filter(pk=self.request.address_id).delete()


class GetAddress(actions.Action):

    type_validators = {
        'address_id': [validators.is_uuid4],
    }

    field_validators = {
        'address_id': {
            valid_address: 'DOES_NOT_EXIST',
        }
    }

    def run(self, *args, **kwargs):
        address = models.Address.objects.get(pk=self.request.address_id)
        address.to_protobuf(self.response.address)
