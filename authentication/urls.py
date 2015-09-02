from django.conf.urls import (
    include,
    patterns,
    url,
)

from . import views

urlpatterns = patterns(
    '',
    url(r'^oauth2/', include('authentication.oauth2.urls')),
    url(r'^saml/', include('authentication.saml.urls')),
    url(r'^success/', views.AuthSuccessView.as_view(), name='auth-success'),
    url(r'^error/', views.AuthErrorView.as_view(), name='auth-error'),
)
