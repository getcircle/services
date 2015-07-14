from base64 import b64decode

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
    Team,
)
from profiles.models import (
    Profile,
    Tag,
)


class Search(mixins.PreRunParseTokenMixin, actions.Action):

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
                Tag.objects.filter(organization_id=self.organization_id),
                self._get_group_category_queryset(),
            )
        else:
            category = self.request.category
            category_queryset = None
            if category == search_pb2.PROFILES:
                category_queryset = Profile.objects.filter(organization_id=self.organization_id)
            elif category == search_pb2.TEAMS:
                category_queryset = Team.objects.filter(organization_id=self.organization_id)
            elif category == search_pb2.LOCATIONS:
                category_queryset = Location.objects.filter(organization_id=self.organization_id)
            elif category == search_pb2.SKILLS:
                category_queryset = Tag.objects.filter(
                    organization_id=self.organization_id,
                    type=profile_containers.TagV1.SKILL,
                )
            elif category == search_pb2.INTERESTS:
                category_queryset = Tag.objects.filter(
                    organization_id=self.organization_id,
                    type=profile_containers.TagV1.INTEREST,
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

        category_to_container_key = {}
        results_by_category = {}
        for result in results:
            container = self._get_container(result)
            value = container.FromString(b64decode(result.meta['data']))
            if container is profile_containers.ProfileV1:
                category = search_pb2.PROFILES
                container_key = 'profiles'
            elif container is organization_containers.TeamV1:
                category = search_pb2.TEAMS
                container_key = 'teams'
            elif container is organization_containers.LocationV1:
                category = search_pb2.LOCATIONS
                container_key = 'locations'
            elif container is profile_containers.TagV1:
                container_key = 'tags'
                if value.tag_type == profile_containers.TagV1.SKILL:
                    category = search_pb2.SKILLS
                else:
                    category = search_pb2.INTERESTS
            elif container is group_containers.GroupV1:
                category = search_pb2.GROUPS
                container_key = 'groups'

            results_by_category.setdefault(category, []).append(value)
            category_to_container_key.setdefault(category, container_key)

        for category, values in results_by_category.iteritems():
            container = self.response.results.add()
            container_key = category_to_container_key[category]
            container.category = category
            # XXX need to have a way of fetching more for the particular cateogry
            getattr(container, container_key).extend(values[:5])
