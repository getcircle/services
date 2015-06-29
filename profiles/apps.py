from django.apps import AppConfig as BaseAppConfig
import watson

from services.search import SearchAdapter


class ProfileSearchAdapter(SearchAdapter):

    def get_title(self, obj):
        return ' '.join([obj.first_name, obj.last_name])

    def get_description(self, obj):
        return obj.title


class TagSearchAdapter(SearchAdapter):

    def get_title(self, obj):
        return obj.name


class AppConfig(BaseAppConfig):
    name = 'profiles'

    def ready(self):
        Profile = self.get_model('Profile')
        watson.register(
            Profile,
            ProfileSearchAdapter,
            fields=('title', 'email', 'first_name', 'last_name', 'nickname'),
        )

        Tag = self.get_model('Tag')
        watson.register(Tag, TagSearchAdapter, fields=('name', 'type'))
