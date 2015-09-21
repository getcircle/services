from django.conf.urls import (
    patterns,
    url,
)

from . import views

urlpatterns = patterns(
    '',
    url('^(?P<domain>\w+)/$', views.SAMLHandler.as_view(), name='saml-handler'),
)
