from django.apps import AppConfig as DjangoAppConfig
import watson


class TeamSearchAdapter(watson.SearchAdapter):

    def get_title(self, obj):
        return obj.name


class LocationSearchAdapter(watson.SearchAdapter):

    def get_title(self, obj):
        return obj.name


class AppConfig(DjangoAppConfig):
    name = 'organizations'

    def ready(self):
        Team = self.get_model('Team')
        watson.register(Team, TeamSearchAdapter, fields=('name',), store=('name',))

        Location = self.get_model('Location')
        watson.register(
            Location,
            LocationSearchAdapter,
            fields=('name',),
            store=('name', 'image_url',),
        )
