import logging

from django.conf import settings
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView
from service import metrics

from . import actions
from .. import tasks

logger = logging.getLogger(__name__)


class ProcessEmailView(APIView):

    def perform_authentication(self, request, *args, **kwargs):
        token = request.data.get('token')
        if not token:
            raise exceptions.NotAuthenticated()

        if token not in settings.EMAIL_HOOK_SECRET_KEYS:
            raise exceptions.AuthenticationFailed()

        source = request.data.get('source')
        if not source:
            logger.error('source not found', extra={'request': request._request})
            raise exceptions.ParseError('source is required')

        try:
            ses_source = request.data['recipients']
        except KeyError:
            logger.error('recipients not provided', extra={'request': request._request})
            raise exceptions.ParseError('recipients is required')

        if not isinstance(ses_source, basestring):
            logger.error('recipients not a string', extra={'request': request._request})
            raise exceptions.ParseError('recipients must be a string')

        domain = actions.extract_domain(source, ses_source)
        request.source = actions.get_details_for_source(domain, source)
        if not request.source:
            logger.error('unknown source', extra={'request': request._request})
            raise exceptions.NotFound()

    def post(self, request, *args, **kwargs):
        message_id = request.data.get('message_id')
        if not message_id:
            logger.error('message_id is required', extra={'request': request._request})
            raise exceptions.ParseError('message_id is required')

        processing_time = request.data.get('processing_time')
        if processing_time:
            metrics.timing(
                'service.hooks.email.aws.processing_time',
                processing_time,
                use_ms=False,
            )

        # XXX draft should be something the view accepts as a parameter
        tasks.create_post_from_message.delay(
            message_id=message_id,
            organization_id=request.source.organization_id,
            by_profile_id=request.source.profile_id,
            notify_email=request.source.email,
            domain=request.source.domain,
            draft=False,
        )
        return Response()
