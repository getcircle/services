import logging

from django.http import HttpResponse
from django.utils.module_loading import import_string
from rest_framework import status
from rest_framework.views import APIView
from service import settings as service_settings
from service_protobufs import soa_pb2

from .authentication import (
    delete_authentication_cookie,
    set_authentication_cookie,
)

logger = logging.getLogger(__name__)


class ServicesView(APIView):

    def __init__(self, *args, **kwargs):
        super(ServicesView, self).__init__(*args, **kwargs)
        self.transport = import_string(service_settings.DEFAULT_TRANSPORT)

    def perform_authentication(self, request):
        request.auth

    def handle_exception(self, exc):
        response = super(ServicesView, self).handle_exception(exc)
        # Clear the cookie if it failed to authenticate the user. This allows
        # the user to re-login.
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            logger.warning('deleting invalid authentication cookie', extra={
                'request': self.request,
            })
            delete_authentication_cookie(response)
        return response

    def post(self, request, *args, **kwargs):
        # XXX handle errors if the request.body fails to serialize
        service_request = soa_pb2.ServiceRequestV1.FromString(request.body)
        # XXX: handle errors if the token fails to parse
        if not request.auth:
            service_request.control.token = ''
        elif (
            not service_request.control.token and
            hasattr(request.successful_authenticator, 'get_token')
        ):
            token = request.successful_authenticator.get_token(request)
            service_request.control.token = token

        serialized_request = service_request.SerializeToString()
        service_response = self.transport.process_request(service_request, serialized_request)
        response = HttpResponse(
            service_response.SerializeToString(),
            content_type='application/x-protobuf',
        )
        if not request.auth and service_response.control.token:
            set_authentication_cookie(response, service_response.control.token)
        elif service_request.control.token and not service_response.control.token:
            delete_authentication_cookie(response, service_request.control.token)
        return response

    def get(self, request, *args, **kwargs):
        return HttpResponse('OK', content_type='text')
