from django.apps import AppConfig as DjangoAppConfig
import watson

from services.search import SearchAdapter


class TeamSearchAdapter(SearchAdapter):

    def get_protobuf(self, obj):
        return obj.to_protobuf(path=obj.get_path())

    def get_title(self, obj):
        return obj.name


class LocationSearchAdapter(SearchAdapter):

    def get_protobuf(self, obj):
        return obj.to_protobuf(
            address=obj.address.as_dict(),
        )

    def get_title(self, obj):
        return obj.name


class AppConfig(DjangoAppConfig):
    name = 'organizations'

    def ready(self):
        Team = self.get_model('Team')
        watson.register(Team, TeamSearchAdapter, fields=('name',))

        Location = self.get_model('Location')
        watson.register(Location, LocationSearchAdapter, fields=('name',))
