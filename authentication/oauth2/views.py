import urllib

from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from protobufs.services.user import containers_pb2 as user_containers
from rest_framework.views import APIView
import service.control


def redirect_with_query_params(name, query_params=None, *args, **kwargs):
    url = reverse(name, *args, kwargs=kwargs)
    if query_params:
        url = '%s?%s' % (
            url,
            urllib.urlencode(query_params),
        )
    return redirect(url)


class OAuth2Handler(APIView):

    def _handle_error(self, error_or_request):
        error = error_or_request
        if hasattr(error, 'GET'):
            error = error.GET.get('error_description', 'invalid_request')

        parameters = {'error': error}
        return redirect_with_query_params(
            'oauth2-error',
            provider=self.provider_name,
            query_params=parameters,
        )

    def _complete_authorization(self, code, state):
        client = service.control.Client('user')
        try:
            response = client.call_action(
                'complete_authorization',
                provider=self.provider_value,
                oauth2_details={'code': code, 'state': state},
            )
        except service.control.CallActionError as e:
            return self._handle_error(', '.join(e.response.errors))

        parameters = {
            'user': urllib.base64.b64encode(response.result.user.SerializeToString()),
            'identity': urllib.base64.b64encode(response.result.identity.SerializeToString()),
            'oauth_sdk_details': urllib.base64.b64encode(
                response.result.oauth_sdk_details.SerializeToString()
            ),
        }
        return redirect_with_query_params(
            'oauth2-success',
            provider=self.provider_name,
            query_params=parameters,
        )

    def _parse_provider(self):
        self.provider_name = self.kwargs['provider']
        provider_map = dict(
            map(lambda x: (x[0].lower(), x[1]), user_containers.IdentityV1.ProviderV1.items())
        )
        self.provider_value = provider_map[self.provider_name]

    def get(self, request, *args, **kwargs):
        try:
            self._parse_provider()
        except KeyError:
            return self._handle_error('invalid provider')

        try:
            code = request.GET['code']
            state = request.GET['state']
        except KeyError:
            return self._handle_error(request)

        return self._complete_authorization(code, state)


class ConnectionSuccessView(TemplateView):

    template_name = 'connection-success.html'


class ConnectionErrorView(TemplateView):

    template_name = 'connection-error.html'
