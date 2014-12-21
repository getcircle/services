from django.http import HttpResponse
from django.utils.module_loading import import_string
from rest_framework.views import APIView
from service import settings as service_settings
from service_protobufs import soa_pb2


class ServicesView(APIView):

    def __init__(self, *args, **kwargs):
        super(ServicesView, self).__init__(*args, **kwargs)
        self.transport = import_string(service_settings.DEFAULT_TRANSPORT)

    def post(self, request, *args, **kwargs):
        service_request = soa_pb2.ServiceRequest.FromString(request.body)
        # TODO: come up with a better way to do this
        if not request.auth:
            service_request.control.token = ''

        response_data = self.transport.handle_request(service_request)
        return HttpResponse(
            response_data,
            content_type='application/x-protobuf',
        )
