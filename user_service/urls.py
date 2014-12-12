from django.conf.urls import (
    patterns,
    url,
)
from django.views.decorators.csrf import csrf_exempt

from .views import UserService

urlpatterns = patterns(
    '',
    url(r'^$', csrf_exempt(UserService.as_view())),
)
