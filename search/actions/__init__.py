from base64 import b64decode

from django.utils.module_loading import import_string
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import search_pb2
from service import actions
import service.control
import watson

from services import mixins

from organizations.models import (
    Location,
    LocationMember,
    ReportingStructure,
    Team,
)
from profiles.models import Profile


class Search(mixins.PreRunParseTokenMixin, actions.Action):

    def validate(self, *args, **kwargs):
        super(Search, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.has_attribute and not self.request.attribute_value:
                raise self.ActionFieldError('attribute_value', 'MISSING')
            elif (
                not self.request.has_attribute and
                self.request.attribute_value
            ):
                raise self.ActionFieldError('attribute_value', 'MISSING')

            if self.request.has_attribute and not self.request.has_category:
                raise self.ActionFieldError('category', 'MISSING')

            if self.request.has_attribute and self.request.category != search_pb2.PROFILES:
                raise self.ActionFieldError(
                    'attribute',
                    'attribute is only supported for "PROFILES" category',
                )

    def pre_run(self, *args, **kwargs):
        super(Search, self).pre_run(*args, **kwargs)
        self.organization_id = self.parsed_token.organization_id
        self._container_cache = {}

    def _get_search_kwargs(self):
        kwargs = {}
        if not self.request.has_category:
            kwargs['models'] = (
                Profile.objects.filter(organization_id=self.organization_id),
                Location.objects.filter(organization_id=self.organization_id),
                Team.objects.filter(organization_id=self.organization_id),
            )
        else:
            category = self.request.category
            category_queryset = None
            parameters = {'organization_id': self.organization_id}
            if category == search_pb2.PROFILES:
                if self.request.has_attribute:
                    if self.request.attribute == search_pb2.TEAM_ID:
                        manager_profile_id = Team.objects.values('manager_profile_id').get(
                            id=self.request.attribute_value,
                        )['manager_profile_id']
                        node = ReportingStructure.objects.get(profile_id=manager_profile_id)
                        parameters['id__in'] = node.get_descendants().values_list(
                            'profile_id',
                            flat=True,
                        )
                    elif self.request.attribute == search_pb2.LOCATION_ID:
                        parameters['id__in'] = LocationMember.objects.filter(
                            location_id=self.request.attribute_value,
                            organization_id=self.organization_id,
                        ).values_list('profile_id', flat=True)
                category_queryset = Profile.objects.filter(**parameters)
            elif category == search_pb2.TEAMS:
                category_queryset = Team.objects.filter(**parameters)
            elif category == search_pb2.LOCATIONS:
                category_queryset = Location.objects.filter(**parameters)
            else:
                raise self.ActionFieldError('category')
            kwargs['models'] = (category_queryset,)
        return kwargs

    def _get_container(self, result):
        container_path = result.meta['protobuf']
        if container_path not in self._container_cache:
            self._container_cache[container_path] = import_string(container_path)
        return self._container_cache[container_path]

    def run(self, *args, **kwargs):
        results = watson.search(
            self.request.query,
            **self._get_search_kwargs()
        )

        for result in results[:15]:
            container = self._get_container(result)
            value = container.FromString(b64decode(result.meta['data']))
            if container is profile_containers.ProfileV1:
                container_key = 'profile'
            elif container is organization_containers.TeamV1:
                container_key = 'team'
            elif container is organization_containers.LocationV1:
                container_key = 'location'
            result_container = self.response.results.add()
            getattr(result_container, container_key).CopyFrom(value)
