from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^slack/$', views.SlackViewSet.as_view({'post': 'slash'}), name='hooks-slack-slash'),
]
