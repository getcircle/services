from django.conf.urls import (
    patterns,
    url,
)

from . import views

urlpatterns = patterns('',
    url(r'^(?P<provider>\w+)/$', views.OAuth2LinkedIn.as_view()),
    url(r'^(?P<provider>\w+)/success/$', views.ConnectionSuccessView.as_view()),
)
