from protobufs.services.search.containers import entity_pb2
import service.control

from services.management.base import BaseCommand
from services.token import get_token_for_domain

PAGE_SIZE = 100


def _update_entiites(token, items, entity_type):
    service.control.call_action(
        service='search',
        action='update_entities',
        client_kwargs={'token': token},
        ids=[i.id for i in items],
        type=entity_type,
    )


def _update_paginated_entities(token, service_name, action, return_object_path, entity_type):
    client = service.control.Client(service_name, token=token)
    next_page = 1
    while next_page:
        response = client.call_action(
            action,
            control={'paginator': {'page': next_page, 'page_size': PAGE_SIZE}},
        )
        _update_entiites(token, getattr(response.result, return_object_path), entity_type)
        if response.control.paginator.page != response.control.paginator.total_pages:
            next_page = response.control.paginator.next_page
        else:
            break


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

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        token = get_token_for_domain(organization_domain)
        entity_types = options['entity_types']
        if entity_pb2.PROFILE in entity_types:
            _update_paginated_entities(
                token,
                'profile',
                'get_profiles',
                'profiles',
                entity_pb2.PROFILE,
            )
        if entity_pb2.TEAM in entity_types:
            _update_paginated_entities(
                token,
                'organization',
                'get_teams',
                'teams',
                entity_pb2.TEAM,
            )
