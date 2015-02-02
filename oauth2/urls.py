from django.conf.urls import (
    patterns,
    url,
)

from . import views

urlpatterns = patterns('',
    url(r'^linkedin/$', views.OAuth2Linkedin.as_view()),
)
