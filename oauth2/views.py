import urllib

from django.shortcuts import redirect
from protobufs.user_service_pb2 import UserService
from rest_framework.views import APIView
import service.control


class OAuth2Linkedin(APIView):

    def _handle_error(self, error_or_request):
        error = error_or_request
        if hasattr(error, 'GET'):
            error = error.GET.get('error_description', 'invalid_request')

        params = {'error': error}
        return redirect('/oauth2/linkedin/error/?%s' % (urllib.urlencode(params),))

    def _complete_authorization(self, code, state):
        client = service.control.Client('user')
        try:
            response = client.call_action(
                'complete_authorization',
                provider=UserService.LINKEDIN,
                oauth2_details={'code': code, 'state': state},
            )
        except client.CallActionError as e:
            return self._handle_error(', '.join(e.response.errors))

        parameters = {
            'user': response.result.user.SerializeToString(),
            'identity': response.result.identity.SerializeToString(),
        }
        return redirect('/oauth2/linkedin/success/?%s' % (urllib.urlencode(parameters),))

    def get(self, request, *args, **kwargs):
        try:
            code = request.GET['code']
            state = request.GET['state']
        except KeyError:
            return self._handle_error(request)

        return self._complete_authorization(code, state)
