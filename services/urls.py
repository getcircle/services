from django.conf.urls import (
    include,
    patterns,
    url,
)
from django.contrib import admin
# from django.views.decorators.csrf import csrf_exempt

from users.views import ConnectLinkedInView

from . import views

urlpatterns = patterns('',
    url(r'^$', views.ServicesView.as_view()),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^oauth2/', include('oauth2.urls')),
)
