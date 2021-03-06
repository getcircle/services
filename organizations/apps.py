from django.apps import AppConfig as DjangoAppConfig
import watson

from services.search import SearchAdapter
from services.token import make_admin_token


class TeamSearchAdapter(SearchAdapter):

    def get_protobuf(self, obj):
        return obj.to_protobuf(token=make_admin_token(organization_id=obj.organization_id))

    def get_title(self, obj):
        return obj.name or ''


class LocationSearchAdapter(SearchAdapter):

    def get_protobuf(self, obj):
        return obj.to_protobuf(token=make_admin_token(organization_id=obj.organization_id))

    def get_title(self, obj):
        return obj.name

    def get_description(self, obj):
        description = [
            obj.address_1,
            obj.address_2,
            obj.city,
            obj.region,
            obj.country_code,
            obj.postal_code
        ]
        return ' '.join([value for value in description if value and value.strip()])


class AppConfig(DjangoAppConfig):
    name = 'organizations'

    def ready(self):
        Team = self.get_model('Team')
        watson.register(Team, TeamSearchAdapter, fields=('name',))

        Location = self.get_model('Location')
        watson.register(Location, LocationSearchAdapter, fields=('name',))
