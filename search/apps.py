from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = 'search'

    def ready(self):
        from . import receivers  # NOQA - don't import signal receivers until the app is ready
