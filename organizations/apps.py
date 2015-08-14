from django.apps import AppConfig as DjangoAppConfig
import watson

from services.search import SearchAdapter
from services.token import make_admin_token
from .mixins import (
    LocationProfileStatsMixin,
    TeamProfileStatsMixin,
)


class TeamSearchAdapter(SearchAdapter, TeamProfileStatsMixin):

    def get_protobuf(self, obj):
        return obj.to_protobuf(token=make_admin_token(organization_id=obj.organization_id))

    def get_title(self, obj):
        return obj.name or ''


class LocationSearchAdapter(SearchAdapter, LocationProfileStatsMixin):

    def get_title(self, obj):
        return obj.name


class AppConfig(DjangoAppConfig):
    name = 'organizations'

    def ready(self):
        Team = self.get_model('Team')
        watson.register(Team, TeamSearchAdapter, fields=('name',))

        Location = self.get_model('Location')
        watson.register(Location, LocationSearchAdapter, fields=('name',))
