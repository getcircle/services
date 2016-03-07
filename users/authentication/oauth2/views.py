from protobufs.services.user import containers_pb2 as user_containers
from rest_framework.views import APIView
import service.control

from ..utils import authorization_redirect


class OAuth2Handler(APIView):

    def _handle_error(self, error_or_request):
        error = error_or_request
        if hasattr(error, 'GET'):
            error = error.GET.get('error_description', 'invalid_request')

        parameters = {'error': error}
        return authorization_redirect(name='auth-error', query_params=parameters)

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

        protobuf_parameters = {
            'user': response.result.user,
            'identity': response.result.identity,
            'google_credentials': response.result.google_credentials,
        }
        parameters = {
            'next_path': response.result.next_path,
        }
        return authorization_redirect(
            name='auth-success',
            redirect_uri=response.result.redirect_uri,
            query_params=parameters,
            protobuf_query_params=protobuf_parameters,
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
