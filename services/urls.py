from django.conf.urls import (
    patterns,
    url,
)
from django.views.decorators.csrf import csrf_exempt

from .views import ServicesView

urlpatterns = patterns(
    '',
    url(r'^$', csrf_exempt(ServicesView.as_view())),
)
