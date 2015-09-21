from django.conf.urls import (
    patterns,
    url,
)

from . import views

urlpatterns = patterns(
    '',
    url(r'^(?P<provider>\w+)/$', views.OAuth2Handler.as_view(), name='oauth2-handler'),
)
