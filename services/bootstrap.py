from django.conf import settings
from django.utils.module_loading import import_string
from protobufs import (
    request_registry_pb2,
    response_registry_pb2,
)
import service.control
from service.transports import local


class Bootstrap(object):

    @classmethod
    def bootstrap(cls):
        print 'bootstrapping application...'
        cls.localize_servers()
        cls.load_protobuf_registries()
        cls.start_metrics()

    @classmethod
    def start_metrics(cls):
        """Start DataDog metrics"""
        service.control.start_metrics_handler(api_key=settings.DATADOG_API_KEY)

    @classmethod
    def localize_servers(cls):
        for service_string in settings.LOCALIZED_SERVICES:
            server = import_string(service_string)
            local.instance.localize_server(server)

    @classmethod
    def load_protobuf_registries(cls):
        service.control.set_protobufs_request_registry(request_registry_pb2)
        service.control.set_protobufs_response_registry(response_registry_pb2)
