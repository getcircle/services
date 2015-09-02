from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect
from rest_framework.views import APIView
from saml2 import entity
import service.control

from .. import utils


class SAMLHandler(APIView):

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
        # XXX return the user's token as a query parameter. we should ensure that this is SSL only
        return redirect(reverse('auth-success'))
