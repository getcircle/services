from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = 'team'

    def ready(self):
        from . import receivers  # NOQA (must be done when the app is ready)
