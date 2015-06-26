from protobufs.services.profile import containers_pb2 as profile_containers
from protobufs.services.search.containers import search_pb2
from service import actions
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

    def _copy_meta_to_container(self, content_type, container, meta):
        for key, value in meta.iteritems():
            mapping = content_type.model_class().model_to_protobuf_mapping
            key = mapping and mapping.get(key, key) or key
            if value is not None:
                setattr(container, key, value)

    def pre_run(self, *args, **kwargs):
        super(Search, self).pre_run(*args, **kwargs)
        self.organization_id = self.parsed_token.organization_id

    def run(self, *args, **kwargs):
        results = watson.search(
            self.request.query,
            models=(
                Profile.objects.filter(organization_id=self.organization_id),
                Location.objects.filter(organization_id=self.organization_id),
                Team.objects.filter(organization_id=self.organization_id),
                Tag.objects.filter(organization_id=self.organization_id),
                GoogleGroup.objects.filter(organization_id=self.organization_id),
            ),
        ).select_related('content_type')

        category_to_container_key = {}
        results_by_category = {}
        for result in results:
            if result.content_type.model == 'profile':
                category = search_pb2.PROFILES
                container_key = 'profiles'
            elif result.content_type.model == 'team':
                category = search_pb2.TEAMS
                container_key = 'teams'
            elif result.content_type.model == 'location':
                category = search_pb2.LOCATIONS
                container_key = 'locations'
            elif result.content_type.model == 'tag':
                container_key = 'tags'
                if result.meta['type'] == profile_containers.TagV1.SKILL:
                    category = search_pb2.SKILLS
                else:
                    category = search_pb2.INTERESTS
            elif result.content_type.model == 'group':
                category = search_pb2.GROUPS
                container_key = 'groups'

            results_by_category.setdefault(category, []).append(result)
            category_to_container_key.setdefault(category, container_key)

        for category, values in results_by_category.iteritems():
            container = self.response.results.add()
            container_key = category_to_container_key[category]
            container.category = category
            for result in values:
                result_container = getattr(container, container_key).add()
                self._copy_meta_to_container(result.content_type, result_container, result.meta)
