from django.apps import AppConfig as DjangoAppConfig
import watson

from services.search import SearchAdapter


class GroupSearchAdapter(SearchAdapter):

    def get_protobuf(self, obj):
        if not isinstance(obj.direct_members_count, int):
            obj.refresh_from_db()
        return obj.to_protobuf()

    def get_title(self, obj):
        return obj.name

    def get_description(self, obj):
        return obj.description or ''


class AppConfig(DjangoAppConfig):
    name = 'group'

    def ready(self):
        GoogleGroup = self.get_model('GoogleGroup')
        watson.register(GoogleGroup, GroupSearchAdapter, fields=('email', 'display_name', 'name'))