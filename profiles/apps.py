from django.apps import AppConfig as BaseAppConfig
import watson


class ProfileSearchAdapter(watson.SearchAdapter):

    def get_title(self, obj):
        return ' '.join([obj.first_name, obj.last_name])

    def get_description(self, obj):
        return obj.title


class TagSearchAdapter(watson.SearchAdapter):

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
            store=('title', 'email', 'first_name', 'last_name', 'nickname', 'email', 'image_url'),
        )

        Tag = self.get_model('Tag')
        watson.register(Tag, TagSearchAdapter, fields=('name', 'type'), store=('name', 'type'))
