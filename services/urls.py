from django.conf.urls import (
    include,
    patterns,
    url,
)

from . import views

urlpatterns = patterns('',
    url(r'^$', views.ServicesView.as_view()),
    url(r'^p/', include('api.urls')),
    url(r'^auth/', include('authentication.urls')),
)
