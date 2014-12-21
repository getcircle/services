from django.http import HttpResponse
from django.utils.module_loading import import_string
from django.views.generic import View

from service import settings as service_settings
from service_protobufs import soa_pb2


class ServicesView(View):

    def __init__(self, *args, **kwargs):
        super(ServicesView, self).__init__(*args, **kwargs)
        print 'instantiating ServiceView'
        self.transport = import_string(service_settings.DEFAULT_TRANSPORT)

    def post(self, request, *args, **kwargs):
        service_request = soa_pb2.ServiceRequest.FromString(request.body)
        response_data = self.transport.handle_request(service_request)
        return HttpResponse(
            response_data,
            content_type='application/x-protobuf',
        )
