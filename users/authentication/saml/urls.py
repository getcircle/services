from django.conf.urls import (
    patterns,
    url,
)

from . import views

urlpatterns = patterns(
    '',
    url('^(?P<domain>[A-Za-z0-9\-_]+)/$', views.SAMLHandler.as_view(), name='saml-handler'),
)
