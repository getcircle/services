from copy import copy
import uuid

from cacheops import cached_as
import django.db
from protobufs.services.common import containers_pb2 as common_containers
from service import (
    actions,
    validators,
)
import service.control
from service import metrics

from services import mixins
from services.token import parse_token
from . import models


def valid_organization(organization_id):
    return models.Organization.objects.filter(pk=organization_id).exists()


def valid_organization_with_domain(domain):
    return models.Organization.objects.filter(domain=domain).exists()


def valid_team(team_id):
    return models.Team.objects.filter(pk=team_id).exists()


def valid_address(address_id):
    return models.Address.objects.filter(pk=address_id).exists()


def valid_location(location_id):
    return models.Location.objects.filter(pk=location_id).exists()


class TeamPermissionsMixin(mixins.PreRunParseTokenMixin):

    @property
    def requester_profile(self):
        if not hasattr(self, '_requester_profile'):
            self._requester_profile = service.control.get_object(
                service='profile',
                action='get_profile',
                return_object='profile',
                client_kwargs={'token': self.token},
                profile_id=self.parsed_token.profile_id,
            )
        return self._requester_profile

    def get_permissions(self, team):
        permissions = common_containers.PermissionsV1()
        if self.parsed_token.is_admin() or self.requester_profile.is_admin:
            permissions.can_edit = True
            permissions.can_add = True
            permissions.can_delete = True
        return permissions


class TeamProfileStatsMixin(object):

    def _fetch_profile_stats(self, team_ids):
        result = {}
        if team_ids:
            client = service.control.Client('profile', token=self.token)
            response = client.call_action('get_profile_stats', team_ids=team_ids)
            result = dict((stat.id, stat.count) for stat in response.result.stats)
        return result


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

    # XXX this should be driven by the token
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


class CreateTeam(TeamPermissionsMixin, actions.Action):

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


class UpdateTeam(TeamPermissionsMixin, actions.Action):

    required_fields = ('team',)

    field_validators = {
        'team.id': {
            valid_team: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        team = models.Team.objects.get(pk=self.request.team.id)

        permissions = self.get_permissions(team)
        if not permissions.can_edit:
            raise self.PermissionDenied()

        team.update_from_protobuf(self.request.team)
        team.save()
        team.to_protobuf(self.response.team, path=team.get_path())
        self.response.team.permissions.CopyFrom(permissions)


class GetTeam(TeamPermissionsMixin, TeamProfileStatsMixin, actions.Action):

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
        profile_stats = self._fetch_profile_stats([str(team.id)])
        team.to_protobuf(
            self.response.team,
            path=team.get_path(),
            profile_count=profile_stats.get(str(team.id), 0),
        )
        self.response.team.permissions.CopyFrom(self.get_permissions(team))


class GetTeamDescendants(TeamPermissionsMixin, actions.Action):

    required_fields = ('team_ids',)
    type_validators = {
        'team_ids': [validators.is_uuid4_list],
    }

    def validate(self, *args, **kwargs):
        super(GetTeamDescendants, self).validate(*args, **kwargs)
        field_names = map(lambda x: x.attname, models.Team._meta.fields)
        if self.request.attributes:
            self.attributes = filter(lambda x: x in field_names, self.request.attributes)
            if len(self.attributes) != len(self.request.attributes):
                raise self.ActionFieldError('attributes', 'INVALID')

            # NB: Raw queries must always contain the primary key
            if models.Team._meta.pk.attname not in self.attributes:
                self.attributes.append('id')
        else:
            self.attributes = ['*']

        self.query_attributes = copy(self.attributes)
        if '*' not in self.attributes:
            # NB: We inspect the path to perform bulk lookups so query for that as
            # well. We don't include it in self.attributes since we only want those
            # to be the attributes the caller specified
            if 'path' not in self.query_attributes:
                self.query_attributes.append('path')

    def _direct_report_team_query(self):
        return 'SELECT %s FROM %s WHERE path ? array[%s] ORDER BY "name"' % (
            ','.join(self.query_attributes),
            models.Team._meta.db_table,
            ''.join(self._build_lquery_placeholders()),
        )

    def _build_lquery_placeholders(self):
        placeholders = []
        for index, _ in enumerate(self.request.team_ids):
            placeholder = '%s::lquery'
            if index != len(self.request.team_ids) - 1:
                placeholder += ','
            placeholders.append(placeholder)
        return placeholders

    def _build_lqueries(self, team_ids, depth=None):
        lqueries = []
        for team_id in team_ids:
            # get the hex value for the lquery
            hex_value = uuid.UUID(team_id, version=4).hex
            lqueries.append('*.%s.*{1,%s}' % (hex_value, self._get_depth()))
        return lqueries

    def _get_depth(self):
        depth = ''
        if self.request.depth > 0:
            depth = self.request.depth
        return depth

    def run(self, *args, **kwargs):
        metrics.gauge(
            'service.action.get_team_descendants.request.team_ids.gauge',
            len(self.request.team_ids),
        )

        # TODO we should be passing organization_id here, make it so we have
        # easy access to the caller's organization_id and other important
        # values in all actions
        @cached_as(models.Team, extra=''.join(self.request.team_ids))
        def _get_descendants_block():
            return list(models.Team.objects.raw(
                self._direct_report_team_query(),
                self._build_lqueries(self.request.team_ids),
            ))

        response_teams = 0
        for team_id in self.request.team_ids:
            container = self.response.descendants.add()
            container.parent_team_id = team_id
            hex_value = uuid.UUID(team_id, version=4).hex
            for team in _get_descendants_block():
                path_parts = team.path.split('.')
                if hex_value in path_parts:
                    should_add = False
                    remaining = len(path_parts) - (path_parts.index(hex_value) + 1)
                    if self.request.depth:
                        should_add = remaining == self.request.depth
                    else:
                        should_add = remaining != 0

                    if should_add:
                        team_container = container.teams.add()
                        parameters = {}
                        if self.request.attributes:
                            parameters['only'] = self.attributes
                        else:
                            parameters['path'] = team.get_path()
                        team.to_protobuf(team_container, **parameters)
                        if not self.request.attributes or (
                            self.request.attributes and
                            'permissions' in self.request.attributes
                        ):
                            team_container.permissions.CopyFrom(self.get_permissions(team))
            response_teams += len(container.teams)
        metrics.gauge('service.action.get_team_descendants.response.teams.gauge', response_teams)


class GetTeams(TeamPermissionsMixin, TeamProfileStatsMixin, actions.Action):

    type_validators = {
        'organization_id': [validators.is_uuid4],
        'location_id': [validators.is_uuid4],
    }

    field_validators = {
        'organization_id': {
            valid_organization: 'DOES_NOT_EXIST',
        }
    }

    def _get_teams_by_organization_id(self):
        return models.Team.objects.filter(
            organization_id=self.request.organization_id,
        )

    def _get_teams_by_location_id(self):
        client = service.control.Client('profile', token=self.token)
        response = client.call_action(
            'get_attributes_for_profiles',
            location_id=self.request.location_id,
            distinct=True,
            attributes=['team_id'],
        )
        return models.Team.objects.filter(
            id__in=[attribute.value for attribute in response.result.attributes],
        )

    def _get_paths_in_bulk(self, teams):
        path_ids = set()
        for team in teams:
            path_ids.update(team.path.split('.'))
        path_values = models.Team.objects.filter(pk__in=path_ids).values(
            'id',
            'name',
            'owner_id',
        )
        # NB: use the hex value of the id as the key since thats what makes up the paths
        return dict((item['id'].hex, item) for item in path_values)

    def run(self, *args, **kwargs):
        if self.request.organization_id:
            teams = self._get_teams_by_organization_id()
        else:
            teams = self._get_teams_by_location_id()

        paginator = self.get_paginator(teams)
        page = self.get_page(paginator)
        path_dict = self._get_paths_in_bulk(page.object_list)
        stats_dict = self._fetch_profile_stats([str(item.id) for item in page.object_list])

        def add_team(item, repeated_container):
            container = repeated_container.add()
            item.to_protobuf(
                container,
                path=item.get_path(path_dict=path_dict),
                profile_count=stats_dict.get(str(item.id), 0),
            )
            container.permissions.CopyFrom(self.get_permissions(item))

        self.paginated_response(
            self.response.teams,
            teams,
            add_team,
            paginator=paginator,
            page=page,
        )


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


class CreateLocation(actions.Action):

    type_validators = {
        'location.organization_id': [validators.is_uuid4],
        'location.address.id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            location = models.Location.objects.from_protobuf(
                self.request.location,
            )
        except django.db.IntegrityError:
            raise self.ActionFieldError('location', 'DUPLICATE')
        location.to_protobuf(self.response.location)


class UpdateLocation(actions.Action):

    type_validators = {
        'location.id': [validators.is_uuid4],
    }

    field_validators = {
        'location.id': {
            valid_location: 'DOES_NOT_EXIST',
        }
    }

    def run(self, *args, **kwargs):
        location = models.Location.objects.get(pk=self.request.location.id)
        location.update_from_protobuf(self.request.location)
        location.save()
        location.to_protobuf(self.response.location)


class BaseLocationAction(actions.Action):

    def _fetch_profile_stats(self, locations):
        client = service.control.Client('profile', token=self.token)
        response = client.call_action(
            'get_profile_stats',
            location_ids=[str(location.id) for location in locations],
        )
        return dict((stat.id, stat.count) for stat in response.result.stats)


class GetLocation(BaseLocationAction):

    type_validators = {
        'location_id': [validators.is_uuid4],
    }

    field_validators = {
        'location_id': {
            valid_location: 'DOES_NOT_EXIST',
        },
    }

    def validate(self, *args, **kwargs):
        super(GetLocation, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.HasField('name') and not self.request.HasField('organization_id'):
                raise self.ActionFieldError('organization_id', 'REQUIRED')

    def run(self, *args, **kwargs):
        parameters = {}
        if self.request.location_id:
            parameters['pk'] = self.request.location_id
        elif self.request.name:
            parameters['name'] = self.request.name
            parameters['organization_id'] = self.request.organization_id
        else:
            raise self.ActionError('FAILURE', ('FAILURE', 'missing parameters'))

        location = models.Location.objects.select_related('address').get(**parameters)
        profile_stats = self._fetch_profile_stats([location])
        location.to_protobuf(
            self.response.location,
            address=location.address.as_dict(),
            profile_count=profile_stats.get(str(location.id), 0),
        )


class GetLocations(mixins.PreRunParseTokenMixin, BaseLocationAction):

    def run(self, *args, **kwargs):
        locations = models.Location.objects.select_related('address').filter(
            organization_id=self.parsed_token.organization_id,
        )
        if not locations:
            return

        profile_stats = self._fetch_profile_stats(locations)
        for location in locations:
            container = self.response.locations.add()
            location.to_protobuf(
                container,
                address=location.address.as_dict(),
                profile_count=profile_stats.get(str(location.id), 0),
            )


class CreateToken(actions.Action):

    def validate(self, *args, **kwargs):
        super(CreateToken, self).validate(*args, **kwargs)
        if not self.is_error():
            self.service_token = parse_token(self.token)
            if not self.service_token.organization_id:
                raise self.ActionFieldError('token.organization_id', 'MISSING')

            if not validators.is_uuid4(self.service_token.organization_id):
                raise self.ActionFieldError('token.organization_id', 'INVALID')

            if not self.service_token.is_admin() and not self.service_token.user_id:
                raise self.ActionFieldError('token.user_id', 'MISSING')

            if (
                not self.service_token.is_admin() and
                not validators.is_uuid4(self.service_token.user_id)
            ):
                raise self.ActionFieldError('token.user_id', 'INVALID')

    def run(self, *args, **kwargs):
        if not valid_organization(self.service_token.organization_id):
            raise self.ActionFieldError('token.organization_id', 'DOES_NOT_EXIST')

        token = models.Token.objects.create(
            requested_by_user_id=self.service_token.user_id,
            organization_id=self.service_token.organization_id,
        )
        token.to_protobuf(self.response.token)


class GetTokens(actions.Action):

    def validate(self, *args, **kwargs):
        super(GetTokens, self).validate(*args, **kwargs)
        if not self.is_error():
            self.service_token = parse_token(self.token)
            if not validators.is_uuid4(self.service_token.organization_id):
                raise self.ActionFieldError('token.organization_id', 'INVALID')

    def run(self, *args, **kwargs):
        if not valid_organization(self.service_token.organization_id):
            raise self.ActionFieldError('token.organization_id', 'DOES_NOT_EXIST')

        tokens = models.Token.objects.filter(organization_id=self.service_token.organization_id)
        self.paginated_response(
            self.response.tokens,
            tokens,
            lambda item, container: item.to_protobuf(container.add()),
        )


class PreRunParseTokenMixin(object):

    def pre_run(self, *args, **kwargs):
        self.parsed_token = parse_token(self.token)


class EnableIntegration(PreRunParseTokenMixin, actions.Action):

    required_fields = ('integration', 'integration.integration_type',)

    def _default_google_group_scopes(self):
        return (
            'https://www.googleapis.com/auth/admin.directory.user',
            'https://www.googleapis.com/auth/admin.directory.group',
            'https://www.googleapis.com/auth/apps.groups.settings',
        )

    def _read_only_google_group_scopes(self):
        return (
            'https://www.googleapis.com/auth/admin.directory.user.readonly',
            'https://www.googleapis.com/auth/admin.directory.group.readonly',
            'https://www.googleapis.com/auth/apps.groups.settings',
        )

    def _get_details_object(self):
        details = self.request.integration.google_groups
        if not len(details.scopes):
            if details.read_only:
                scopes = self._read_only_google_group_scopes()
            else:
                scopes = self._default_google_group_scopes()

            details.scopes.extend(scopes)
        return details

    def run(self, *args, **kwargs):
        try:
            integration = models.Integration.objects.from_protobuf(
                self.request.integration,
                organization_id=self.parsed_token.organization_id,
                details=self._get_details_object(),
            )
        except django.db.IntegrityError:
            raise self.ActionFieldError('integration.integration_type', 'DUPLICATE')

        integration.to_protobuf(self.response.integration)


class DisableIntegration(PreRunParseTokenMixin, actions.Action):

    required_fields = ('integration_type',)

    def _get_integration(self):
        try:
            integration = models.Integration.objects.get(
                organization_id=self.parsed_token.organization_id,
                type=self.request.integration_type,
            )
        except models.Integration.DoesNotExist:
            raise self.ActionFieldError('integration_type', 'DOES_NOT_EXIST')
        return integration

    def run(self, *args, **kwargs):
        integration = self._get_integration()
        integration.delete()


class GetIntegration(DisableIntegration):

    def run(self, *args, **kwargs):
        integration = self._get_integration()
        integration.to_protobuf(self.response.integration)
