from common import utils
import django.db
from django.db.models import Count
from django.utils import timezone
from itsdangerous import BadSignature
from protobufs.services.history import containers_pb2 as history_containers
from protobufs.services.organization.containers import integration_pb2
from protobuf_to_dict import protobuf_to_dict
from service import (
    actions,
    validators,
)
import service.control

from services.history import action_container_for_update
from services.mixins import PreRunParseTokenMixin
from services.token import parse_token
from . import models
from .mixins import (
    LocationPermissionsMixin,
    TeamPermissionsMixin,
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

    field_validators = {
        'domain': {
            valid_organization_with_domain: 'DOES_NOT_EXIST',
        },
    }

    exception_to_error_map = {
        BadSignature: 'FORBIDDEN',
    }

    def _get_organization(self):
        parameters = {}
        if self.request.domain:
            parameters['domain'] = self.request.domain
        else:
            parsed_token = parse_token(self.token)
            parameters['pk'] = parsed_token.organization_id
        return models.Organization.objects.get(**parameters)

    def run(self, *args, **kwargs):
        organization = self._get_organization()
        if self.token:
            organization.to_protobuf(
                self.response.organization,
                fields=self.request.fields,
                inflations=self.request.inflations,
            )
        else:
            organization.to_protobuf(
                self.response.organization,
                # XXX look into not exposing id
                fields={'only': ('image_url', 'domain', 'name', 'id')},
                inflations={'disabled': True},
            )


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

        if request_description.value != (team.description and team.description.value):
            request_description.by_profile_id = self.parsed_token.profile_id
            request_description.changed = str(timezone.now())
            action = action_container_for_update(
                instance=team,
                field_name='description',
                new_value=request_description,
                action_type=history_containers.UPDATE_DESCRIPTION,
            )
        return action

    def run(self, *args, **kwargs):
        team = models.Team.objects.get(pk=self.request.team.id)

        permissions = self.get_permissions(team)
        if not permissions.can_edit:
            raise self.PermissionDenied()

        action = self._get_update_description_action(team)
        team.update_from_protobuf(self.request.team)
        team.save()
        if action:
            service.control.call(
                'history',
                'record_action',
                client_kwargs={'token': self.token},
                action_kwargs={'action': action},
            )
        team.to_protobuf(self.response.team, token=self.token)
        self.response.team.permissions.CopyFrom(permissions)


class GetTeam(TeamPermissionsMixin, actions.Action):

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
        team.to_protobuf(self.response.team, token=self.token)
        self.response.team.permissions.CopyFrom(self.get_permissions(team))


class GetTeams(TeamPermissionsMixin, actions.Action):

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
        if self.request.ids:
            parameters['id__in'] = self.request.ids

        teams = models.Team.objects.filter(**parameters)
        self.paginated_response(
            self.response.teams,
            teams,
            lambda item, container: item.to_protobuf(container.add()),
        )


class GetTeamsForProfileIds(PreRunParseTokenMixin, actions.Action):

    required_fields = ('profile_ids',)
    type_validators = {
        'profile_ids': [validators.is_uuid4_list],
    }

    def run(self, *args, **kwargs):
        reporting_details = models.ReportingStructure.objects.filter(
            organization_id=self.parsed_token.organization_id,
            profile_id__in=self.request.profile_ids,
        )
        manager_ids = set([r.manager_id for r in reporting_details])
        teams = models.Team.objects.filter(
            organization_id=self.parsed_token.organization_id,
            manager_profile_id__in=manager_ids,
        )
        team_dict = dict((t.manager_profile_id, t) for t in teams)
        for report in reporting_details:
            container = self.response.profiles_teams.add()
            container.profile_id = str(report.profile_id)
            team = team_dict.get(report.manager_id)
            if team:
                container.team.CopyFrom(team.to_protobuf(fields=self.request.fields))


class CreateLocation(PreRunParseTokenMixin, actions.Action):

    def run(self, *args, **kwargs):
        try:
            location = models.Location.objects.from_protobuf(
                self.request.location,
                organization_id=self.parsed_token.organization_id,
            )
        except django.db.IntegrityError:
            raise self.ActionFieldError('location', 'DUPLICATE')
        location.to_protobuf(self.response.location)


class BaseLocationAction(LocationPermissionsMixin, actions.Action):

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
                    inflations={'only': ['contact_methods']},
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

        if request_description.value != (location.description and location.description.value):
            request_description.changed = str(timezone.now())
            request_description.by_profile_id = self.parsed_token.profile_id
            action = action_container_for_update(
                instance=location,
                field_name='description',
                new_value=request_description,
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
            service.control.call(
                'history',
                'record_action',
                client_kwargs={'token': self.token},
                action_kwargs={'action': action},
            )

        points_of_contact = self._fetch_points_of_contact([location])
        location.to_protobuf(
            self.response.location,
            points_of_contact=points_of_contact.get(str(location.id), []),
            token=self.token,
        )


class GetLocation(BaseLocationAction):

    type_validators = {
        'location_id': [validators.is_uuid4],
    }

    def run(self, *args, **kwargs):
        parameters = {
            'organization_id': self.parsed_token.organization_id,
        }
        lookup_field = 'location_id'
        if self.request.name:
            parameters['name'] = self.request.name
            lookup_field = 'name'
        else:
            parameters['pk'] = self.request.location_id

        try:
            location = models.Location.objects.get(**parameters)
        except models.Location.DoesNotExist:
            raise self.ActionFieldError(lookup_field, 'DOES_NOT_EXIST')

        points_of_contact = self._fetch_points_of_contact([location])
        location.to_protobuf(
            self.response.location,
            points_of_contact=points_of_contact.get(str(location.id), []),
            token=self.token,
        )
        self.response.location.permissions.CopyFrom(self.get_permissions(location))


class GetLocations(BaseLocationAction):

    type_validators = {
        'profile_id': (validators.is_uuid4,)
    }

    def run(self, *args, **kwargs):
        parameters = {'organization_id': self.parsed_token.organization_id}
        if self.request.ids:
            parameters['id__in'] = self.request.ids

        locations = models.Location.objects.filter(**parameters)
        if self.request.profile_id:
            locations = locations.filter(
                members__profile_id=self.request.profile_id,
                members__organization_id=self.parsed_token.organization_id,
            )

        if not locations:
            return

        if utils.should_inflate_field('profile_count', self.request.inflations):
            member_stats = models.LocationMember.objects.filter(
                location_id__in=[location.id for location in locations],
                organization_id=self.parsed_token.organization_id,
            ).values('location_id').annotate(profiles=Count('id'))
            member_stats = dict((d['location_id'], d['profiles']) for d in member_stats)
        else:
            member_stats = {}

        points_of_contact = {}
        if utils.should_inflate_field('points_of_contact', self.request.inflations):
            points_of_contact = self._fetch_points_of_contact(locations)

        for location in locations:
            container = self.response.locations.add()
            location.to_protobuf(
                container,
                profile_count=member_stats.get(location.id, 0),
                points_of_contact=points_of_contact.get(str(location.id), []),
            )
            if utils.should_inflate_field('permissions', self.request.inflations):
                container.permissions.CopyFrom(self.get_permissions(location))


class GetLocationMembers(PreRunParseTokenMixin, actions.Action):

    required_fields = ('location_id',)
    type_validators = {
        'location_id': (validators.is_uuid4,),
    }
    field_validators = {
        'location_id': {
            valid_location: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        member_profile_ids = models.LocationMember.objects.filter(
            organization_id=self.parsed_token.organization_id,
            location_id=self.request.location_id,
        ).values_list('profile_id', flat=True)
        self.paginated_response(
            self.response.member_profile_ids,
            member_profile_ids,
            lambda item, container: container.append(str(item)),
        )


class AddLocationMembers(PreRunParseTokenMixin, actions.Action):

    required_fields = (
        'location_id',
        'profile_ids',
    )
    type_validators = {
        'location_id': (validators.is_uuid4,),
        'profile_ids': (validators.is_uuid4_list,),
    }
    field_validators = {
        'location_id': {
            valid_location: 'DOES_NOT_EXIST',
        },
    }

    def run(self, *args, **kwargs):
        objects = [models.LocationMember(
            organization_id=self.parsed_token.organization_id,
            profile_id=profile_id,
            location_id=self.request.location_id,
        ) for profile_id in self.request.profile_ids]
        models.LocationMember.objects.bulk_create(objects)


class EnableIntegration(PreRunParseTokenMixin, actions.Action):

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
        details_path = self.request.integration.WhichOneof('details')
        details = getattr(self.request.integration, details_path)
        return details

    def run(self, *args, **kwargs):
        parameters = {
            'organization_id': self.parsed_token.organization_id,
            'details': self._get_details_object(),
        }
        if self.request.integration.slack_slash_command:
            parameters['provider_uid'] = self.request.integration.provider_uid

        try:
            integration = models.Integration.objects.from_protobuf(
                self.request.integration,
                **parameters
            )
        except django.db.IntegrityError:
            raise self.ActionFieldError('integration.integration_type', 'DUPLICATE')

        integration.to_protobuf(self.response.integration)


class DisableIntegration(PreRunParseTokenMixin, actions.Action):

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

    def _get_integration(self):
        parameters = {}
        if self.request.provider_uid:
            parameters['provider_uid'] = self.request.provider_uid
        else:
            parameters['organization_id'] = self.parsed_token.organization_id

        try:
            integration = models.Integration.objects.get(
                type=self.request.integration_type,
                **parameters
            )
        except models.Integration.DoesNotExist:
            raise self.ActionFieldError('integration_type', 'DOES_NOT_EXIST')
        return integration

    def run(self, *args, **kwargs):
        integration = self._get_integration()
        integration.to_protobuf(self.response.integration)


class ReportingStructureAction(PreRunParseTokenMixin, actions.Action):

    def _add_direct_reports(self, manager_profile_id, direct_reports_profile_ids):
        manager, created = models.ReportingStructure.objects.get_or_create(
            profile_id=manager_profile_id,
            organization_id=self.parsed_token.organization_id,
            defaults={
                'added_by_profile_id': self.parsed_token.profile_id,
            },
        )
        # move any existing reports to the new manager
        existing_reports = models.ReportingStructure.objects.filter(
            profile_id__in=direct_reports_profile_ids,
            organization_id=self.parsed_token.organization_id,
        )
        for report in existing_reports:
            report.manager = manager
            report.save()

        existing_ids = [str(report.profile_id) for report in existing_reports]
        # NB: django-mptt doesn't support bulk_update. creating objects handles
        # creating the default fields we need and we don't expect to add many
        # direct reports so this should be acceptable
        for profile_id in direct_reports_profile_ids:
            if profile_id not in existing_ids:
                models.ReportingStructure.objects.create(
                    profile_id=profile_id,
                    manager=manager,
                    organization_id=self.parsed_token.organization_id,
                    added_by_profile_id=self.parsed_token.profile_id,
                )

        team, created = models.Team.objects.get_or_create(
            manager_profile_id=manager_profile_id,
            organization_id=self.parsed_token.organization_id,
            defaults={
                'created_by_profile_id': self.parsed_token.profile_id,
            },
        )
        return team, created


class AddDirectReports(ReportingStructureAction):

    required_fields = (
        'profile_id',
        'direct_reports_profile_ids',
    )
    type_validators = {
        'profile_id': (validators.is_uuid4,),
        'direct_reports_profile_ids': (validators.is_uuid4_list,),
    }

    def run(self, *args, **kwargs):
        team, created = self._add_direct_reports(
            self.request.profile_id,
            self.request.direct_reports_profile_ids,
        )
        team.to_protobuf(self.response.team)
        self.response.created = created


class SetManager(ReportingStructureAction):

    required_fields = (
        'manager_profile_id',
        'profile_id',
    )

    type_validators = {
        'manager_profile_id': (validators.is_uuid4,),
        'profile_id': (validators.is_uuid4,),
    }

    def run(self, *args, **kwargs):
        team, created = self._add_direct_reports(
            self.request.manager_profile_id,
            [self.request.profile_id],
        )
        team.to_protobuf(self.response.team)


class GetProfileReportingDetails(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'profile_id': (validators.is_uuid4,),
    }

    def run(self, *args, **kwargs):
        parameters = {
            'organization_id': self.parsed_token.organization_id,
            'profile_id': self.parsed_token.profile_id,
        }
        if self.request.profile_id:
            parameters['profile_id'] = self.request.profile_id

        try:
            position = models.ReportingStructure.objects.get(**parameters)
        except models.ReportingStructure.DoesNotExist:
            return

        # get the team the profile is on if applicable (only a root node wouldn't have a team)
        if not position.is_root_node():
            team = models.Team.objects.get(
                manager_profile_id=position.manager_id,
                organization_id=self.parsed_token.organization_id,
            )
            team.to_protobuf(self.response.team, description=None)
            self.response.manager_profile_id = str(position.manager_id)

            peers = position.get_siblings().filter(
                organization_id=self.parsed_token.organization_id,
            ).values_list('profile_id', flat=True)
            self.response.peers_profile_ids.extend(map(str, peers))

        # if the profile has direct reports, export the team and reports they manage
        if position.get_descendant_count():
            team = models.Team.objects.get(
                manager_profile_id=position.profile_id,
                organization_id=self.parsed_token.organization_id,
            )
            team.to_protobuf(self.response.manages_team, description=None)
            direct_reports = position.get_children().filter(
                organization_id=self.parsed_token.organization_id,
            ).values_list('profile_id', flat=True)
            self.response.direct_reports_profile_ids.extend(map(str, direct_reports))


class GetTeamReportingDetails(PreRunParseTokenMixin, actions.Action):

    required_fields = ('team_id',)
    type_validators = {
        'team_id': (validators.is_uuid4,),
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
        manager = models.ReportingStructure.objects.get(
            profile_id=team.manager_profile_id,
            organization_id=self.parsed_token.organization_id,
        )
        manager_profile = service.control.get_object(
            'profile',
            'get_profile',
            client_kwargs={'token': self.token},
            return_object='profile',
            profile_id=str(manager.profile_id),
            inflations={'disabled': True},
        )
        self.response.manager.CopyFrom(manager_profile)

        children = manager.get_children().filter(
            organization_id=self.parsed_token.organization_id,
        )
        child_team_manager_ids = [member.profile_id for member in children if (
            member.manager_id == manager.profile_id and
            member.get_descendant_count()
        )]
        if child_team_manager_ids:
            teams = models.Team.objects.filter(
                organization_id=self.parsed_token.organization_id,
                manager_profile_id__in=child_team_manager_ids,
            )
            for team in teams:
                container = self.response.child_teams.add()
                team.to_protobuf(container, description=None)


class GetDescendants(PreRunParseTokenMixin, actions.Action):

    type_validators = {
        'profile_id': (validators.is_uuid4,),
        'team_id': (validators.is_uuid4,),
    }

    def validate(self, *args, **kwargs):
        super(GetDescendants, self).validate(*args, **kwargs)
        if not self.is_error():
            if not self.request.profile_id and not self.request.team_id:
                raise self.ActionFieldError('profile_id', 'MISSING')

    def _get_profile_ids_with_node(self, node):
        if self.request.direct:
            queryset = node.get_children()
        else:
            queryset = node.get_descendants()

        return list(queryset.filter(
            organization_id=self.parsed_token.organization_id,
        ).values_list('profile_id', flat=True))

    def _populate_with_profile_id(self):
        try:
            node = models.ReportingStructure.objects.get(
                pk=self.request.profile_id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.ReportingStructure.DoesNotExist:
            raise self.ActionFieldError('profile_id', 'DOES_NOT_EXIST')

        profile_ids = self._get_profile_ids_with_node(node)
        return profile_ids

    def _populate_with_team_id(self):
        try:
            team = models.Team.objects.values('manager_profile_id').get(
                pk=self.request.team_id,
                organization_id=self.parsed_token.organization_id,
            )
        except models.Team.DoesNotExist:
            raise self.ActionFieldError('team_id', 'DOES_NOT_EXIST')

        node = models.ReportingStructure.objects.get(
            profile_id=team['manager_profile_id'],
            organization_id=self.parsed_token.organization_id,
        )
        profile_ids = self._get_profile_ids_with_node(node)
        if not self.request.direct:
            # add the manager profile id
            profile_ids.append(node.profile_id)
        return profile_ids

    def run(self, *args, **kwargs):
        if self.request.team_id:
            profile_ids = self._populate_with_team_id()
        else:
            profile_ids = self._populate_with_profile_id()
        self.paginated_response(
            self.response.profile_ids,
            profile_ids,
            lambda item, container: container.append(str(item)),
        )


class GetSSO(actions.Action):

    required_fields = ('organization_domain',)

    def run(self, *args, **kwargs):
        try:
            sso = models.SSO.objects.get(
                organization__domain=self.request.organization_domain,
            )
        except models.SSO.DoesNotExist:
            raise self.ActionFieldError('organization_domain', 'DOES_NOT_EXIST')

        sso.to_protobuf(self.response.sso)
