from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = 'post'

    def ready(self):
        from . import receivers  # NOQA (must be done when the app is ready)
