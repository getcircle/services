from django.conf import settings
from django.http import Http404
from protobufs.services.user import containers_pb2 as user_containers
from rest_framework.views import APIView
import service.control

from ..utils import authorization_redirect


class SAMLHandler(APIView):

    def post(self, request, *args, **kwargs):
        domain = kwargs['domain']
        client = service.control.Client('user')
        try:
            response = client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.SAML,
                saml_details={
                    'domain': domain,
                    'saml_response': request.data['SAMLResponse'],
                    'relay_state': request.data['RelayState'],
                },
            )
        except service.control.CallActionError:
            # XXX add some logging here and return to an error view for iOS
            raise Http404

        redirect_uri = settings.USER_SERVICE_AUTH_SUCCESS_REDIRECT_URI
        if response.result.redirect_uri:
            redirect_uri = response.result.redirect_uri

        protobuf_parameters = {
            'user': response.result.user,
            'identity': response.result.identity,
            'saml_details': response.result.saml_details,
        }
        return authorization_redirect(
            redirect_uri=redirect_uri,
            protobuf_query_params=protobuf_parameters,
        )
