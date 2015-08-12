import uuid

import django.db
from django.db.models import Count
from django.utils import timezone
from protobufs.services.history import containers_pb2 as history_containers
from protobuf_to_dict import protobuf_to_dict
from service import (
    actions,
    validators,
)
import service.control

from services.history import action_container_for_update
from services.token import parse_token
from . import models
from .mixins import (
    LocationPermissionsMixin,
    LocationProfileStatsMixin,
    TeamPermissionsMixin,
    TeamProfileStatsMixin,
)


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


class UpdateTeam(TeamPermissionsMixin, actions.Action):

    required_fields = ('team',)

    field_validators = {
        'team.id': {
            valid_team: 'DOES_NOT_EXIST',
        },
    }

    def _get_update_description_action(self, team):
        action = None
        request_description = self.request.team.description
        if not request_description.value and not team.description:
            return action

        if request_description.value != (team.description and team.description['value']):
            request_description.by_profile_id = self.parsed_token.profile_id
            request_description.changed = str(timezone.now())
            action = action_container_for_update(
                instance=team,
                field_name='description',
                new_value=protobuf_to_dict(request_description),
                action_type=history_containers.UPDATE_DESCRIPTION,
            )
        return action

    def run(self, *args, **kwargs):
        team = models.Team.objects.get(pk=self.request.team.id)

        permissions = self.get_permissions(team)
        if not permissions.can_edit:
            raise self.PermissionDenied()

        action = self._get_update_description_action(team)
        team.update_from_protobuf(self.request.team, self.parsed_token.profile_id)
        team.save()
        if action:
            service.control.call_action(
                'history',
                'record_action',
                client_kwargs={'token': self.token},
                action=action,
            )
        team.to_protobuf(self.response.team)
        self.response.team.permissions.CopyFrom(permissions)


class GetTeam(TeamPermissionsMixin, TeamProfileStatsMixin, actions.Action):

    type_validators = {
        'team_id': [validators.is_uuid4],
    }

    field_validators = {
        'team_id': {
            valid_team: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        team = models.Team.objects.get(
            pk=self.request.team_id,
            organization_id=self.parsed_token.organization_id,
        )
        team.to_protobuf(self.response.team)
        self.response.team.permissions.CopyFrom(self.get_permissions(team))


class CreateLocation(actions.Action):

    type_validators = {
        'location.organization_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        try:
            location = models.Location.objects.from_protobuf(
                self.request.location,
            )
        except django.db.IntegrityError:
            raise self.ActionFieldError('location', 'DUPLICATE')
        location.to_protobuf(self.response.location)


class BaseLocationAction(LocationProfileStatsMixin, LocationPermissionsMixin, actions.Action):

    def _fetch_points_of_contact(self, locations):
        location_to_profiles = {}
        for location in locations:
            location_to_profiles.setdefault(str(location.id), [])
            if location.points_of_contact_profile_ids:
                profiles = service.control.get_object(
                    service='profile',
                    action='get_profiles',
                    client_kwargs={'token': self.token},
                    return_object='profiles',
                    ids=map(str, location.points_of_contact_profile_ids),
                )
                location_to_profiles[str(location.id)] = map(protobuf_to_dict, profiles)
        return location_to_profiles


class UpdateLocation(BaseLocationAction):

    type_validators = {
        'location.id': [validators.is_uuid4],
    }

    field_validators = {
        'location.id': {
            valid_location: 'DOES_NOT_EXIST',
        }
    }

    def _get_update_description_action(self, location):
        action = None
        request_description = self.request.location.description
        if not request_description.value and not location.description:
            return action

        if request_description.value != (location.description and location.description['value']):
            request_description.changed = str(timezone.now())
            request_description.by_profile_id = self.parsed_token.profile_id
            action = action_container_for_update(
                instance=location,
                field_name='description',
                new_value=protobuf_to_dict(request_description),
                action_type=history_containers.UPDATE_DESCRIPTION,
            )
        return action

    def run(self, *args, **kwargs):
        location = models.Location.objects.get(pk=self.request.location.id)

        permissions = self.get_permissions(location)
        if not permissions.can_edit:
            raise self.PermissionDenied()

        action = self._get_update_description_action(location)
        location.update_from_protobuf(self.request.location)
        location.save()
        if action:
            service.control.call_action(
                'history',
                'record_action',
                client_kwargs={'token': self.token},
                action=action,
            )

        points_of_contact = self._fetch_points_of_contact([location])
        location.to_protobuf(
            self.response.location,
            points_of_contact=points_of_contact.get(str(location.id), []),
        )


class GetLocation(BaseLocationAction):

    type_validators = {
        'location_id': [validators.is_uuid4],
    }

    field_validators = {
        'location_id': {
            valid_location: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        location = models.Location.objects.get(pk=self.request.location_id)
        points_of_contact = self._fetch_points_of_contact([location])
        location.to_protobuf(
            self.response.location,
            points_of_contact=points_of_contact.get(str(location.id), []),
        )
        self.response.location.permissions.CopyFrom(self.get_permissions(location))


class GetLocations(BaseLocationAction):

    def run(self, *args, **kwargs):
        locations = models.Location.objects.filter(
            organization_id=self.parsed_token.organization_id,
        )
        if not locations:
            return

        member_stats = models.LocationMember.objects.filter(
            location_id__in=[location.id for location in locations],
            organization_id=self.parsed_token.organization_id,
        ).values('location_id').annotate(profiles=Count('id'))
        member_stats = dict((d['location_id'], d['profiles']) for d in member_stats)

        points_of_contact = self._fetch_points_of_contact(locations)
        for location in locations:
            container = self.response.locations.add()
            location.to_protobuf(
                container,
                profile_count=member_stats.get(location.id, 0),
                points_of_contact=points_of_contact.get(str(location.id), []),
            )
            container.permissions.CopyFrom(self.get_permissions(location))


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
