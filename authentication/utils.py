import tempfile
import urlparse

from django.conf import settings
from django.core.urlresolvers import reverse
from saml2 import (
    BINDING_HTTP_POST,
    BINDING_HTTP_REDIRECT,
)
from saml2.client import Saml2Client
from saml2.config import Config as Saml2Config


def get_acs_url(domain, scheme='http'):
    saml_url = reverse('saml-handler', kwargs={'domain': domain})
    return urlparse.urlunparse((scheme, settings.HOSTNAME, saml_url, None, None, None))


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
