import uuid
import django.db
from service import (
    actions,
    validators,
)

from . import (
    containers,
    models,
)


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
            organization = models.Organization.objects.create(
                name=self.request.name,
                domain=self.request.domain,
            )
        except django.db.IntegrityError:
            self.note_error(
                'FIELD_ERROR',
                ('domain', 'DUPLICATE'),
            )
        return organization

    def run(self, *args, **kwargs):
        model = self._create_organization()
        if model:
            containers.copy_organization_to_container(
                model,
                self.response.organization,
            )


class CreateTeam(actions.Action):

    type_validators = {
        'owner_id': [validators.is_uuid4],
        'organization_id': [validators.is_uuid4],
        'child_of': [validators.is_uuid4],
    }

    field_validators = {
        'organization_id': {
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
                    parent_team.organization_id.hex != self.request.organization_id
                ):
                    self.note_field_error('child_of', 'DOES_NOT_EXIST')

    def _resolve_path(self, team_id):
        if not self.request.child_of:
            return team_id

        parent_team = self._get_parent_team()
        return parent_team.path + '.' + team_id

    # XXX this should be transaction.commit_on_success or whatever the django
    # 1.7 equivalent is
    def _create_team(self):
        team_id = uuid.uuid4()
        path = self._resolve_path(team_id.hex)
        return models.Team.objects.create(
            id=team_id,
            name=self.request.name,
            owner_id=self.request.owner_id,
            organization_id=self.request.organization_id,
            path=path,
        )

    def run(self, *args, **kwargs):
        team = self._create_team()
        containers.copy_team_to_container(team, self.response.team)


class CreateAddress(actions.Action):

    type_validators = {
        'address.organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        address = models.Address.objects.create(
            organization_id=self.request.address.organization_id,
            name=self.request.address.name,
            address_1=self.request.address.address_1,
            address_2=self.request.address.address_2,
            city=self.request.address.city,
            region=self.request.address.region,
            postal_code=self.request.address.postal_code,
            country_code=self.request.address.country_code,
        )
        containers.copy_address_to_container(address, self.response.address)


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
