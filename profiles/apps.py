import arrow
from django.apps import AppConfig as BaseAppConfig
import watson

from services.search import SearchAdapter
from services.token import make_admin_token


class ProfileSearchAdapter(SearchAdapter):

    def get_title(self, obj):
        return ' '.join([obj.first_name, obj.last_name])

    def get_description(self, obj):
        return obj.title or ''

    def get_protobuf(self, obj):
        return obj.to_protobuf(token=make_admin_token(organization_id=obj.organization_id))


class TagSearchAdapter(SearchAdapter):

    def get_title(self, obj):
        return obj.name


class ProfileStatusSearchAdapter(SearchAdapter):

    def get_title(self, obj):
        return obj.value or ''

    def get_description(self, obj):
        profile = obj.profile.to_protobuf(
            token=make_admin_token(organization_id=obj.organization_id),
        )
        return ' '.join([profile.full_name, profile.display_title])

    def get_content(self, obj):
        return arrow.get(obj.created).format('MMMM D, YYYY')


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

        ProfileStatus = self.get_model('ProfileStatus')
        watson.register(
            ProfileStatus.objects.exclude(value__isnull=True),
            ProfileStatusSearchAdapter,
            fields=('value'),
        )
