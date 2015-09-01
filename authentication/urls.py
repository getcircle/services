from django.conf.urls import (
    patterns,
    url,
)

from . import views

urlpatterns = patterns('',
    url(r'^oauth2/(?P<provider>\w+)/$', views.OAuth2LinkedIn.as_view()),
    url(r'^oauth2/(?P<provider>\w+)/success/$', views.ConnectionSuccessView.as_view()),
)
