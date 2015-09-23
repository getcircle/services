User Service
============

The user service is responsible for managing the life cycle of users in our system.

Third Party Identities
----------------------

A user can have multiple identities associated with their account. These
identities are third party services like Google or Linkedin. By adding an
identity, the user is giving us access to their profile information within the
service as well as some API access to the resources within the service where
applicable.

Identities can also be used to authenticate the user. If we trust the identity
provider (ie. Google), we'll respect the details of the user (email address)
that come from the service.


Authentication
---------------

We support multiple backends for authenticating users within our system:

    - Internal (email/password)
    - Google (a Google identity for the user)
    - SAML (if a domain is provided that we have SSO metadata for)

For facilitated login (OAuth2 and SAML), the client acts as an intermediary
between the identity provider (Google/Okta) and our API.

Login Flow
-----------

OAuth2 & SAML on Web:
- the client calls `get_authentication_instructions`
    - provides `email` and a `redirect_uri`
- the client redirects to the `authorization_url` that is returned with
  `get_authentication_instructions`
- the user authenticates with the identity provider
- the identity provider redirects back to the API server
- the API verifies the details from the identity provider and saves the identity
  for the user.
- the API redirects to the `redirect_uri` that was provided (as long as it is
  a white listed value)
    - in the redirect, the API returns the user's identity as well as some
      authentication state that can be used to log the user in
      - for OAuth2, this is oauth_sdk_details (code, id_token)
      - for SAML, this is saml_details (auth_state)
- the client uses the the identity to authenticate the user

OAuth2 & SAML on iOS:
- the client opens a webview to the `authorization_url` that was returned by
  `get_authentication_instructions`
- the user authenticates with the identity provider
- the identity provider redirects back to the API server
- the API verifies the details from the identity provider and saves the identity
  for the user.
- the API redirects to the default `redirect_uri`
    - in the redirect, the API returns the user's identity as well as some
      authentication state that can be used to log the user in
      - for OAuth2, this is oauth_sdk_details (code, id_token)
      - for SAML, this is saml_details (auth_state)
- the client intercepts the redirect and reads the identity and auth details
- the client uses the the identity to authenticate the user

Login Handlers
--------------

The user service has several views to handle callback requests from identity
providers. The URLs to these views usually need to be configured with our
application with the identity provider.

user/auth/oauth2/<provider>
- handles the OAuth2 callback flow for a given provider

user/auth/saml/<domain>
- handles the SAML callback flow for a given domain

user/auth/success
- default view after a client has successfully authorized with an identity provider

user/auth/error
- default error view if the client failed to authorize with an identity provider

OAuth2 Containers
-----------------

OAuth2DetailsV1
- code
- state

These are the OAuth2 values that are returned after the client has successfully
authenticated with the identity provider. We trade the `code` for an
`access_token` that can be used to make subsequent requests on behalf of the
user.

We are then able to generate the `OAuthSDKDetailsV1` using the `id_token`

OAuthSDKDetailsV1
- code
- id\_token

The `id_token` can be used to verify the user is who he says he is from the
identity provider.
