import logging

from django.conf import settings
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView
import tldextract

from . import actions
from .. import tasks

logger = logging.getLogger(__file__)


class ProcessEmailView(APIView):

    @property
    def extract(self):
        # by default tldextract makes a web request when first initializes and
        # uses a cache file, disable these and just use the default snapshot it
        # comes with
        return tldextract.TLDExtract(suffix_list_url=False, cache_file=False)

    def perform_authentication(self, request, *args, **kwargs):
        token = request.data.get('token')
        if not token:
            raise exceptions.NotAuthenticated()

        if token not in settings.EMAIL_HOOK_SECRET_KEYS:
            raise exceptions.AuthenticationFailed()

        source = request.data.get('source')
        if not source:
            raise exceptions.ParseError('source is required')

        extracted = self.extract(source)
        request.source = actions.get_details_for_source(extracted.domain, source)
        if not request.source:
            raise exceptions.NotFound()

    def post(self, request, *args, **kwargs):
        message_id = request.data.get('message_id')
        if not message_id:
            raise exceptions.ParseError('message_id is required')

        # XXX `draft` should be something the view accepts as a parameter
        tasks.create_post_from_message.delay(
            message_id=message_id,
            organization_id=request.source.organization_id,
            by_profile_id=request.source.profile_id,
            draft=False,
        )
        return Response()
