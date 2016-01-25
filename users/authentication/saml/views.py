import base64
import urlparse

from django.conf import settings
from protobufs.services.user import containers_pb2 as user_containers
from rest_framework.views import APIView
import service.control

from ..utils import authorization_redirect


class SAMLHandler(APIView):

    def _get_organization_redirect_uri(self, domain):
        parts = urlparse.urlsplit(settings.USER_SERVICE_SAML_AUTH_SUCCESS_REDIRECT_URI)
        return urlparse.urlunsplit((
            parts.scheme,
            '%s.%s' % (domain, parts.netloc),
            parts.path,
            parts.query,
            parts.fragment,
        ))

    def post(self, request, *args, **kwargs):
        domain = kwargs['domain']
        redirect_uri = self._get_organization_redirect_uri(domain)

        client = service.control.Client('user')
        try:
            response = client.call_action(
                'complete_authorization',
                provider=user_containers.IdentityV1.OKTA,
                saml_details={
                    'domain': domain,
                    'saml_response': request.data['SAMLResponse'],
                    'relay_state': request.data['RelayState'],
                },
            )
        except service.control.CallActionError as e:
            query_params = {
                'error': ','.join(e.response.errors),
                'domain': domain,
            }
            if query_params['error'] == 'PROFILE_NOT_FOUND':
                user_info = e.response.error_details[0].detail
                query_params['user_info'] = base64.b64encode(user_info)
            return authorization_redirect(redirect_uri=redirect_uri, query_params=query_params)

        protobuf_parameters = {
            'user': response.result.user,
            'identity': response.result.identity,
            'saml_credentials': response.result.saml_credentials,
        }
        return authorization_redirect(
            redirect_uri=redirect_uri,
            protobuf_query_params=protobuf_parameters,
        )
