from django.conf.urls import (
    include,
    patterns,
    url,
)
from django.contrib import admin
from django.views.decorators.csrf import csrf_exempt

from .views import ServicesView

urlpatterns = patterns('',
    url(r'^$', csrf_exempt(ServicesView.as_view())),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
