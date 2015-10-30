from base64 import b64decode

from django.db.models import Q
from django.utils.module_loading import import_string
from protobufs.services.group import containers_pb2 as group_containers
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import search_pb2
from service import actions
import service.control
import watson

from services import mixins

from group.models import GoogleGroup
from organizations.models import (
    Location,
    LocationMember,
    ReportingStructure,
    Team,
)
from profiles.models import (
    Profile,
    ProfileStatus,
    Tag,
)


class Search(mixins.PreRunParseTokenMixin, actions.Action):

    def validate(self, *args, **kwargs):
        super(Search, self).validate(*args, **kwargs)
        if not self.is_error():
            if self.request.HasField('attribute') and not self.request.HasField('attribute_value'):
                raise self.ActionFieldError('attribute_value', 'MISSING')
            elif (
                not self.request.HasField('attribute') and
                self.request.HasField('attribute_value')
            ):
                raise self.ActionFieldError('attribute_value', 'MISSING')

            if self.request.HasField('attribute') and not self.request.HasField('category'):
                raise self.ActionFieldError('category', 'MISSING')

            if self.request.HasField('attribute') and self.request.category != search_pb2.PROFILES:
                raise self.ActionFieldError(
                    'attribute',
                    'attribute is only supported for "PROFILES" category',
                )

    def pre_run(self, *args, **kwargs):
        super(Search, self).pre_run(*args, **kwargs)
        self.organization_id = self.parsed_token.organization_id
        self._container_cache = {}

    def _get_group_category_queryset(self):
        try:
            groups = service.control.get_object(
                service='group',
                action='get_groups',
                client_kwargs={'token': self.token},
                return_object='groups',
                provider=group_containers.GOOGLE,
            )
        except service.control.CallActionError:
            return GoogleGroup.objects.none()

        return GoogleGroup.objects.filter(pk__in=[group.id for group in groups])

    def _get_search_kwargs(self):
        kwargs = {}
        if not self.request.HasField('category'):
            kwargs['models'] = (
                Profile.objects.filter(organization_id=self.organization_id),
                Location.objects.filter(organization_id=self.organization_id),
                Team.objects.filter(organization_id=self.organization_id),
                ProfileStatus.objects.filter(
                    organization_id=self.organization_id,
                ).exclude(Q(value='') | Q(value__isnull=True)),
            )
        else:
            category = self.request.category
            category_queryset = None
            parameters = {'organization_id': self.organization_id}
            if category == search_pb2.PROFILES:
                if self.request.HasField('attribute'):
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
            elif category == search_pb2.SKILLS:
                category_queryset = Tag.objects.filter(
                    type=profile_containers.TagV1.SKILL,
                    **parameters
                )
            elif category == search_pb2.INTERESTS:
                category_queryset = Tag.objects.filter(
                    type=profile_containers.TagV1.INTEREST,
                    **parameters
                )
            elif category == search_pb2.GROUPS:
                category_queryset = self._get_group_category_queryset()
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
            elif container is group_containers.GroupV1:
                container_key = 'group'
            elif container is profile_containers.ProfileStatusV1:
                container_key = 'profile_status'
            result_container = self.response.results.add()
            getattr(result_container, container_key).CopyFrom(value)


class SearchV2(actions.Action):

    def run(self, *args, **kwargs):
        pass
