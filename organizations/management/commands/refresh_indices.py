from protobufs.services.post import containers_pb2 as post_containers
from protobufs.services.search.containers import entity_pb2
import service.control

from services.management.base import BaseCommand
from services.token import make_admin_token
from services.utils import execute_handler_on_paginated_items

from ... import models


def _update_entities(items, token=None, entity_type=None):
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
        _update_entities,
        action_kwargs=kwargs,
        entity_type=entity_type,
    )


class Command(BaseCommand):

    help = 'Refresh the search indices for all organizations.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            help='Organization\'s domain',
        )
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
            '--collections',
            dest='entity_types',
            action='append_const',
            const=entity_pb2.COLLECTION,
            help='Index the collections for the organization',
        )

    def handle(self, *args, **options):
        entity_types = options.get('entity_types') or []
        index_all = not entity_types

        organization_domain = options.get('domain')
        if organization_domain:
            organizations = models.Organization.objects.filter(domain=organization_domain)
        else:
            organizations = models.Organization.objects.all()

        for organization in organizations:
            print '--> updating entities for: %s' % (organization.domain,)
            token = make_admin_token(organization_id=str(organization.id))
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
                    'team',
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
            if entity_pb2.COLLECTION in entity_types or index_all:
                _update_paginated_entities(
                    token,
                    'post',
                    'get_collections',
                    'collections',
                    entity_pb2.COLLECTION,
                )
