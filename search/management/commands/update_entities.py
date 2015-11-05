from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.search.containers import entity_pb2
import service.control

from services.management.base import BaseCommand
from services.token import get_token_for_domain

from ..utils import execute_handler_on_paginated_items


def _update_entiites(items, token=None, entity_type=None):
    service.control.call_action(
        service='search',
        action='update_entities',
        client_kwargs={'token': token},
        ids=[i.id for i in items],
        type=entity_type,
    )


def _update_paginated_entities(
        token,
        service_name,
        action,
        return_object_path,
        entity_type,
        **kwargs
    ):
    execute_handler_on_paginated_items(
        token,
        service_name,
        action,
        return_object_path,
        _update_entiites,
        action_kwargs=kwargs,
        entity_type=entity_type,
    )


class Command(BaseCommand):

    help = 'Index the entities for an organization'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument(
            '--profiles',
            dest='entity_types',
            action='append_const',
            const=entity_pb2.PROFILE,
            help='Index the profiles for the organization',
        )
        parser.add_argument(
            '--teams',
            dest='entity_types',
            action='append_const',
            const=entity_pb2.TEAM,
            help='Index the teams for the organization',
        )
        parser.add_argument(
            '--locations',
            dest='entity_types',
            action='append_const',
            const=entity_pb2.LOCATION,
            help='Index the locations for the organization',
        )
        parser.add_argument(
            '--posts',
            dest='entity_types',
            action='append_const',
            const=entity_pb2.POST,
            help='Index the posts for the organization',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Index all entities for the organization',
        )

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        token = get_token_for_domain(organization_domain)
        entity_types = options.get('entity_types') or []
        index_all = options['all']
        if entity_pb2.PROFILE in entity_types or index_all:
            _update_paginated_entities(
                token,
                'profile',
                'get_profiles',
                'profiles',
                entity_pb2.PROFILE,
            )
        if entity_pb2.TEAM in entity_types or index_all:
            _update_paginated_entities(
                token,
                'organization',
                'get_teams',
                'teams',
                entity_pb2.TEAM,
            )
        if entity_pb2.LOCATION in entity_types or index_all:
            _update_paginated_entities(
                token,
                'organization',
                'get_locations',
                'locations',
                entity_pb2.LOCATION,
            )
        if entity_pb2.POST in entity_types or index_all:
            _update_paginated_entities(
                token,
                'post',
                'get_posts',
                'posts',
                entity_pb2.POST,
                state=post_containers.LISTED,
            )
