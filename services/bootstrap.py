from django.conf import settings
from django.utils.module_loading import import_string
from protobufs.services.registry import (
    requests_pb2,
    responses_pb2,
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
        """Start metrics"""
        handler = import_string(settings.METRICS_HANDLER)
        service.control.set_metrics_handler(handler)
        service.control.start_metrics_handler(use_ms=True, **settings.METRICS_HANDLER_KWARGS)

    @classmethod
    def localize_servers(cls):
        for service_string in settings.LOCALIZED_SERVICES:
            server = import_string(service_string)
            local.instance.localize_server(server)

    @classmethod
    def load_protobuf_registries(cls):
        service.control.set_protobufs_request_registry(requests_pb2)
        service.control.set_protobufs_response_registry(responses_pb2)
