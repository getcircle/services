import urllib

from django.views.generic.base import TemplateView
from django.shortcuts import redirect
from protobufs.services.user import containers_pb2 as user_containers
from rest_framework.views import APIView
import service.control


class OAuth2LinkedIn(APIView):

    def _handle_error(self, error_or_request):
        error = error_or_request
        if hasattr(error, 'GET'):
            error = error.GET.get('error_description', 'invalid_request')

        params = {'error': error}
        return redirect('/oauth2/%s/error/?%s' % (
            self.provider_name,
            urllib.urlencode(params),
        ))

    def _complete_authorization(self, code, state):
        client = service.control.Client('user')
        try:
            response = client.call_action(
                'complete_authorization',
                provider=self.provider_value,
                oauth2_details={'code': code, 'state': state},
            )
        except client.CallActionError as e:
            return self._handle_error(', '.join(e.response.errors))

        parameters = {
            'user': urllib.base64.b64encode(response.result.user.SerializeToString()),
            'identity': urllib.base64.b64encode(response.result.identity.SerializeToString()),
            'oauth_sdk_details': urllib.base64.b64encode(
                response.result.oauth_sdk_details.SerializeToString()
            ),
        }
        return redirect('/oauth2/%s/success/?%s' % (
            self.provider_name,
            urllib.urlencode(parameters),
        ))

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
