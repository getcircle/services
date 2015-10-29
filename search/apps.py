from django.apps import AppConfig as BaseAppConfig
from django.conf import settings
from elasticsearch_dsl import connections


class AppConfig(BaseAppConfig):
    name = 'search'

    def ready(self):
        from . import receivers  # NOQA - don't import signal receivers until the app is ready
        # create the elasticsearch connection
        connection_settings = settings.SEARCH_SERVICE_ELASTICSEARCH
        if connection_settings:
            connections.connections.create_connection(**connection_settings)
