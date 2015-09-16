import urllib

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect
from itsdangerous import (
    BadSignature,
    Signer,
)
from protobufs.services.user.actions import authenticate_user_pb2
from rest_framework.views import APIView
from saml2 import entity
import service.control

from users.providers.base import get_state_token

from .. import utils


class SAMLHandler(APIView):

    def _get_redirect_uri(self, **query_parameters):
        redirect_uri = None
        relay_state = self.request.DATA['RelayState']
        if '.' in relay_state:
            signer = Signer(settings.SECRET_KEY)
            try:
                redirect_uri = signer.unsign(relay_state)
            except (BadSignature, TypeError):
                # XXX add some logging here
                redirect_uri = None

        if redirect_uri is None:
            redirect_uri = reverse('auth-success')

        if query_parameters:
            redirect_uri = '%s?%s' % (
                redirect_uri,
                urllib.urlencode(query_parameters),
            )

        return redirect_uri

    def post(self, request, *args, **kwargs):
        domain = kwargs['domain']
        client = service.control.Client('organization')
        try:
            response = client.call_action('get_sso_metadata', organization_domain=domain)
        except service.control.CallActionError:
            # XXX add some logging here
            raise Http404

        saml_client = utils.get_saml_client(domain, response.result.sso.metadata)
        authn_response = saml_client.parse_authn_request_response(
            self.request.DATA['SAMLResponse'],
            entity.BINDING_HTTP_POST,
        )
        user_info = authn_response.get_subject()
        email = user_info.text
        token = get_state_token(authenticate_user_pb2.RequestV1.SAML, {'email': email})
        redirect_uri = self._get_redirect_uri(provider='saml', state=token)
        return redirect(redirect_uri)
