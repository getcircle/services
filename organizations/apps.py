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
        self.token = make_admin_token(organization_id=obj.organization_id)
        team_id = str(obj.id)
        team_ids = [team_id]
        profile_stats = self.fetch_profile_stats(team_ids)
        child_team_counts = self.fetch_child_team_counts(team_ids)
        return obj.to_protobuf(
            path=obj.get_path(),
            profile_count=profile_stats.get(team_id, 0),
            child_team_count=child_team_counts.get(team_id, 0),
        )

    def get_title(self, obj):
        return obj.name


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
