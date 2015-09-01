from django.conf.urls import (
    include,
    patterns,
    url,
)

urlpatterns = patterns(
    '',
    url(r'^oauth2', include('authentication.oauth2')),
)
