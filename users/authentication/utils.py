import re
import tempfile
import urllib
import urlparse

from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from saml2 import (
    BINDING_HTTP_POST,
    BINDING_HTTP_REDIRECT,
)
from saml2.client import Saml2Client
from saml2.config import Config as Saml2Config
import service.control

from services.token import make_token

from .. import models


def get_acs_url(domain, scheme='http'):
    saml_url = reverse('saml-handler', kwargs={'domain': domain})
    return urlparse.urlunparse((scheme, settings.SERVICES_HOSTNAME, saml_url, None, None, None))


def get_saml_config(domain, metadata):
    temp = tempfile.NamedTemporaryFile()
    with open(temp.name, 'w') as write_file:
        write_file.write(metadata)

    acs_url = get_acs_url(domain)
    https_acs_url = get_acs_url(domain, scheme='https')
    settings = {
        'metadata': {
            'local': [temp.name],
        },
        'service': {
            'sp': {
                'endpoints': {
                    'assertion_consumer_service': [
                        (acs_url, BINDING_HTTP_REDIRECT),
                        (acs_url, BINDING_HTTP_POST),
                        (https_acs_url, BINDING_HTTP_REDIRECT),
                        (https_acs_url, BINDING_HTTP_POST),
                    ],
                },
                # Don't verify that the incoming requests originate from us via
                # the built-in cache for authn request ids in pysaml2
                'allow_unsolicited': True,
                # Don't sign authn requests, since signed requests only make
                # sense in a situation where you control both the SP and IdP
                'authn_requests_signed': False,
                'logout_requests_signed': True,
                'want_assertions_signed': True,
                'want_response_signed': False,
            },
        },
    }
    config = Saml2Config()
    config.load(settings)
    temp.close()
    config.allow_unknown_attributes = True
    return config


def get_saml_client(domain, metadata):
    config = get_saml_config(domain, metadata)
    saml_client = Saml2Client(config=config)
    return saml_client


def get_token(user, client_type):

    def _get_profile(token):
        profile = None
        client = service.control.Client('profile', token=token)
        try:
            response = client.call_action('get_profile')
            profile = response.result.profile
        except service.control.CallActionError:
            profile = None
        return profile

    token, _ = models.Token.objects.get_or_create(
        user_id=user.id,
        client_type=client_type,
        organization_id=user.organization_id,
    )
    # XXX this assumes that we have profiles already set up
    temporary_token = make_token(
        auth_token=token.key,
        auth_token_id=token.id,
        user_id=user.id,
        client_type=client_type,
        organization_id=user.organization_id,
    )
    profile = _get_profile(temporary_token)
    return make_token(
        auth_token=token.key,
        auth_token_id=token.id,
        profile_id=getattr(profile, 'id', None),
        user_id=user.id,
        organization_id=getattr(profile, 'organization_id', None),
        client_type=client_type,
    )


def authorization_redirect(
        name=None,
        redirect_uri=None,
        query_params=None,
        protobuf_query_params=None,
        *args,
        **kwargs
    ):
    if not any([name, redirect_uri]):
        raise TypeError('Must provide either "name" or "redirect_uri"')

    if redirect_uri:
        url = redirect_uri
    else:
        url = reverse(name, *args, kwargs=kwargs)

    parameters = query_params or {}
    if protobuf_query_params:
        for key, value in protobuf_query_params.iteritems():
            parameters[key] = urllib.base64.b64encode(value.SerializeToString())

    if parameters:
        url = '%s?%s' % (
            url,
            urllib.urlencode(parameters),
        )
    return redirect(url)


def valid_redirect_uri(value):
    for regex in settings.USER_SERVICE_ALLOWED_REDIRECT_URIS_REGEX_WHITELIST:
        if re.match(regex, value):
            return True
    return False


def valid_next_path(value):
    return value and value.strip() and len(value) > 1 and value[0] == '/'
