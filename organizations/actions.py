import uuid
import django.db
from service import (
    actions,
    validators,
)

from . import models


def valid_organization(organization_id):
    return models.Organization.objects.filter(pk=organization_id).exists()


def valid_organization_with_domain(domain):
    return models.Organization.objects.filter(domain=domain).exists()


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
            self.note_field_error('organization.domain', 'DUPLICATE')
        return organization

    def run(self, *args, **kwargs):
        model = self._create_organization()
        if model:
            model.to_protobuf(self.response.organization)


class GetOrganization(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    field_validators = {
        'organization_id': {
            valid_organization: 'DOES_NOT_EXIST',
        },
        'organization_domain': {
            valid_organization_with_domain: 'DOES_NOT_EXIST',
        },
    }

    def _get_organization(self):
        parameters = {}
        if self.request.HasField('organization_id'):
            parameters['pk'] = self.request.organization_id
        else:
            parameters['domain'] = self.request.organization_domain
        return models.Organization.objects.get(**parameters)

    def run(self, *args, **kwargs):
        model = self._get_organization()
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
        team = None
        team_id = uuid.uuid4()
        path = self._resolve_path(team_id.hex)
        try:
            team = models.Team.objects.from_protobuf(
                self.request.team,
                id=team_id,
                path=path,
            )
        except django.db.IntegrityError:
            self.note_field_error('team.name', 'DUPLICATE')
        return team

    def run(self, *args, **kwargs):
        team = self._create_team()
        if team:
            team.to_protobuf(self.response.team, path=team.get_path())


class GetTeam(actions.Action):

    type_validators = {
        'team_id': [validators.is_uuid4],
        'organization_id': [validators.is_uuid4],
    }

    field_validators = {
        'team_id': {
            valid_team: 'DOES_NOT_EXIST',
        },
    }

    def validate(self, *args, **kwargs):
        super(GetTeam, self).validate(*args, **kwargs)
        if self.request.name and not self.request.organization_id:
            self.note_field_error('organization_id', 'MISSING')
        if self.request.organization_id and not self.request.name:
            self.note_field_error('name', 'MISSING')

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.team_id:
            parameters['pk'] = self.request.team_id
        else:
            parameters['name'] = self.request.name
            parameters['organization_id'] = self.request.organization_id

        # TODO map this error
        team = models.Team.objects.get(**parameters)
        team.to_protobuf(self.response.team, path=team.get_path())


class GetTeamChildren(actions.Action):

    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    field_validators = {
        'team_id': {
            valid_team: 'DOES_NOT_EXIST',
        },
    }

    def _direct_report_team_query(self):
        return 'SELECT * FROM %s WHERE path ~ %%s ORDER BY "name"' % (models.Team._meta.db_table,)

    def _build_lquery(self, team_id):
        # get the hex value for the lquery
        hex_value = uuid.UUID(team_id, version=4).hex
        return '*.%s.*{1}' % (hex_value,)

    def run(self, *args, **kwargs):
        teams = models.Team.objects.raw(
            self._direct_report_team_query(),
            [self._build_lquery(self.request.team_id)],
        )
        for team in teams:
            container = self.response.teams.add()
            team.to_protobuf(container, path=team.get_path())


class GetTeams(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    field_validators = {
        'organization_id': {
            valid_organization: 'DOES_NOT_EXIST',
        }
    }

    def run(self, *args, **kwargs):
        teams = models.Team.objects.filter(
            organization_id=self.request.organization_id,
        )
        for team in teams:
            result = self.response.teams.add()
            team.to_protobuf(result, path=team.get_path())


class CreateAddress(actions.Action):

    type_validators = {
        'address.organization_id': [validators.is_uuid4],
    }

    def _create_address(self):
        address = None
        try:
            address = models.Address.objects.from_protobuf(
                self.request.address,
            )
        except django.db.IntegrityError:
            self.note_field_error('address.name', 'DUPLICATE')
        return address

    def run(self, *args, **kwargs):
        address = self._create_address()
        if address:
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
        'organization_id': [validators.is_uuid4],
    }

    field_validators = {
        'address_id': {
            valid_address: 'DOES_NOT_EXIST',
        }
    }

    def validate(self, *args, **kwargs):
        super(GetAddress, self).validate(*args, **kwargs)
        if self.request.name and not self.request.organization_id:
            self.note_field_error('organization_id', 'MISSING')
        elif self.request.organization_id and not self.request.name:
            self.note_field_error('name', 'MISSING')

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.address_id:
            parameters['pk'] = self.request.address_id
        else:
            parameters['name'] = self.request.name
            parameters['organization_id'] = self.request.organization_id

        address = models.Address.objects.get(**parameters)
        address.to_protobuf(self.response.address)


class GetAddresses(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        addresses = models.Address.objects.filter(organization_id=self.request.organization_id)
        for address in addresses:
            container = self.response.addresses.add()
            address.to_protobuf(container)


class GetTopLevelTeam(actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        team = models.Team.objects.filter(
            organization_id=self.request.organization_id,
        ).order_by('path')[0]
        team.to_protobuf(self.response.team, path=team.get_path())
