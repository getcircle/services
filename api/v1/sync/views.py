import json
from protobufs.services.organization import containers_pb2 as organization_containers
from protobufs.services.sync.containers import payload_pb2
from rest_framework import (
    exceptions,
    viewsets,
)
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
import service.control

from services.token import make_token


class SyncViewSet(viewsets.ViewSet):

    renderer_classes = (JSONRenderer,)

    def perform_authentication(self, request, *args, **kwargs):
        if isinstance(request.user, organization_containers.OrganizationV1):
            request.organization = request.user
            request.user = None
        else:
            request.organization = None

        if not (request.auth and request.organization):
            raise exceptions.NotAuthenticated()

        request.token = make_token(
            auth_token=request.auth,
            organization_id=request.organization.id,
        )

    def start(self, request, *args, **kwargs):
        client = service.control.Client('sync', token=request.token)
        response = client.call_action('start_sync')
        return Response({'sync_id': response.result.sync_id})

    def _sync_payloads(self, request, payload_key, payload_type):
        client = service.control.Client('sync', token=request.token)
        payload = payload_pb2.PayloadV1()
        payload.payload = json.dumps(request.data[payload_key])
        payload.payload_type = payload_type
        client.call_action('sync_payloads', sync_id=request.data['sync_id'], payloads=[payload])
        return Response()

    def sync_users(self, request, *args, **kwargs):
        return self._sync_payloads(request, 'users', payload_pb2.PayloadV1.USERS)

    def sync_groups(self, request, *args, **kwargs):
        return self._sync_payloads(request, 'groups', payload_pb2.PayloadV1.GROUPS)

    def complete(self, request, *args, **kwargs):
        client = service.control.Client('sync', token=request.token)
        client.call_action('complete_sync', sync_id=request.data['sync_id'])
        return Response()

    def check(self, request, *args, **kwargs):
        return Response()

    def handle_exception(self, exception):
        if isinstance(exception, service.control.CallActionError):
            exception = exceptions.APIException()
        return super(SyncViewSet, self).handle_exception(exception)
