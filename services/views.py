from django.http import HttpResponse
from django.utils.module_loading import import_string
from rest_framework.views import APIView
from service import settings as service_settings
from service_protobufs import soa_pb2

from .authentication import set_authentication_cookie


class ServicesView(APIView):

    def __init__(self, *args, **kwargs):
        super(ServicesView, self).__init__(*args, **kwargs)
        self.transport = import_string(service_settings.DEFAULT_TRANSPORT)

    def perform_authentication(self, request):
        request.auth

    def post(self, request, *args, **kwargs):
        # XXX handle errors if the request.body fails to serialize
        service_request = soa_pb2.ServiceRequestV1.FromString(request.body)
        # XXX: handle errors if the token fails to parse
        if not request.auth:
            service_request.control.token = ''

        serialized_request = service_request.SerializeToString()
        service_response = self.transport.process_request(service_request, serialized_request)
        response = HttpResponse(
            service_response.SerializeToString(),
            content_type='application/x-protobuf',
        )
        if not request.auth and service_response.control.token:
            set_authentication_cookie(
                response,
                service_response.control.token,
                secure=request.is_secure(),
            )
        return response

    def get(self, request, *args, **kwargs):
        return HttpResponse('OK', content_type='text')
