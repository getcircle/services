from django.conf.urls import (
    include,
    url,
)


urlpatterns = [
    url(r'^sync/', include('api.v1.sync.urls')),
]
