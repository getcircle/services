from django.conf.urls import (
    include,
    patterns,
    url,
)

from . import views

urlpatterns = patterns('',
    url(r'^$', views.ServicesView.as_view()),
    url(r'^v1/$', views.ServicesView.as_view()),
    url(r'^p/', include('api.urls')),
    url(r'^user/', include('users.urls')),
)
