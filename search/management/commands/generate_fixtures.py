from collections import namedtuple

from protobuf_to_dict import protobuf_to_dict
import yaml

from services.management.base import BaseCommand
from services.token import get_token_for_domain
from services.utils import execute_handler_on_paginated_items


def _add_fixtures(key):
    def _handler(items, token=None, data=None):
        fixtures = data.setdefault(key, [])
        for container in items:
            fixtures.append(protobuf_to_dict(container))
    return _handler


class Command(BaseCommand):

    help = 'Generate fixtures for search tests'

    def add_arguments(self, parser):
        parser.add_argument('organization_domain', type=str, help='Organization\'s domain')
        parser.add_argument('--output', type=str, help='Optional output path')

    def handle(self, *args, **options):
        organization_domain = options['organization_domain']
        output_path = options.get('output') or 'search/fixtures/%s.yml' % (organization_domain,)
        token = get_token_for_domain(organization_domain)

        FixtureInput = namedtuple(
            'FixtureInput',
            ['service', 'action', 'return_object_path'],
        )
        data = {}
        inputs = [
            FixtureInput('profile', 'get_profiles', 'profiles'),
            FixtureInput('organization', 'get_locations', 'locations'),
            FixtureInput('organization', 'get_teams', 'teams'),
            FixtureInput('post', 'get_posts', 'posts'),
        ]
        for fixture_input in inputs:
            execute_handler_on_paginated_items(
                token,
                fixture_input.service,
                fixture_input.action,
                fixture_input.return_object_path,
                _add_fixtures(fixture_input.return_object_path),
                data=data,
            )

        with open(output_path, 'w') as write_file:
            yaml.dump(data, write_file)
