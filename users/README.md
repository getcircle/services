User Service
============

The user service is responsible for managing the life cycle of users in our system.

Third Party Identities
----------------------

A user can have multiple identities associated with their account. These
identities are third party services like Google or Linkedin. By adding an
identity, the user is giving us access to their profile information within the
service as well as some API access to the resources within the service.

Identities can also be used to authenticate the user. If we trust the identity
provider (ie. Google), we'll respect the details of the user (email address)
that come from the service.


Authentication
---------------

We support multiple backends for authenticating users within our system:

    - Internal (email/password)
    - Google (a Google identity for the user)
    - SAML (if a domain is provided that we have SSO metadata for)

For facilitated login (OAuth2 and SAML), the client acts as an intermediary between the identity provider (Google/Okta) and our API.

Login Flow
----------

- calls `get_authentication_instructions` for the user
    - this returns the authentication backend (and any metadata needed for the
      backend) that should be used to authenticate the user.

for facilitated login (SAML & Google) on the web:
- the client provides a `redirect_uri` with the call to
  `get_authentication_instructions`
- the client redirects to the `authorization_url` that is returned with
  `get_authentication_instructions`
- the user authenticates with the identity provider
- the identity provider redirects back to the API server
- the API verifies the details from the identity provider and generates the JWT
  token for the user
- the API redirects to the `redirect_uri` that was provided (as long as it is
  a white listed value)
    - in the redirect, the API sets an HTTPS only cookie with the JWT for the
      user
- client uses the JWT to fetch the current information for the user

for facilitated login (SAML & Google) on iOS:
- the client opens a webview to the `authorization_url` that was returned by
  `get_authentication_instructions`
- the user authenticates with the identity provider
- the identity provider redirects back to the API server
- the API verifies the details from the identity provider and generates the JWT
  token for the user
- the API redirects to the default success url, with the HTTPS only cookie set
  with the JWT for the user
- the client intercepts the redirect and reads the token from the cookie
- client uses the JWT to fetch the current information for the user

Login Handlers
--------------

The user service has several views to handle callback requests from identity
providers. The URLs to these views usually need to be configured with our
application with the identity provider.

user/auth/oauth2/<provider>
- handles the oauth2 callback flow for a given provider

user/auth/saml/<domain>
- handles the SAML callback flow for a given domain

user/auth/success
- default view after a client has successfully authorized with an identity provider

user/auth/error
- default error view if the client failed to authorize with an identity provider
