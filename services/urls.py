from django.conf.urls import (
    include,
    patterns,
    url,
)

from . import views

urlpatterns = patterns('',
    url(r'^$', views.ServicesView.as_view()),
    url(r'^v1/$', views.ServicesView.as_view()),
    url(r'^user/', include('users.urls')),
    url(r'^hooks/', include('hooks.urls')),
)
