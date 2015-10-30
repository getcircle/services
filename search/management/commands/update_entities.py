from protobufs.services.search.containers import entity_pb2
import service.control
from service.settings import MAX_PAGE_SIZE

from services.management.base import BaseCommand
from services.token import get_token_for_domain


def update_profiles(token):

    def _update_entiites(profiles):
        service.control.call_action(
            service='search',
            action='update_entities',
            client_kwargs={'token': token},
            ids=[p.id for p in response.result.profiles],
            type=entity_pb2.PROFILE,
        )

    client = service.control.Client('profile', token=token)
    next_page = 1
    while next_page:
        response = client.call_action(
            'get_profiles',
            control={'paginator': {'page': next_page, 'page_size': MAX_PAGE_SIZE}},
        )
        _update_entiites(response.result.profiles)
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
            help='Index the profiles',
        )

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        token = get_token_for_domain(organization_domain)
        entity_types = options['entity_types']
        if entity_pb2.PROFILE in entity_types:
            update_profiles(token)
