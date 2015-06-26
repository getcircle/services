from django.apps import AppConfig as DjangoAppConfig
import watson


class GroupSearchAdapter(watson.SearchAdapter):

    def get_title(self, obj):
        return obj.name

    def get_description(self, obj):
        return obj.description


class AppConfig(DjangoAppConfig):
    name = 'group'

    def ready(self):
        GoogleGroup = self.get_model('GoogleGroup')
        watson.register(
            GoogleGroup,
            GroupSearchAdapter,
            fields=('email', 'display_name', 'name'),
            store=('name', 'email', 'display_name', 'description'),
        )
