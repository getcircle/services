from django.conf.urls import url

from .slack import views as SlackViews

urlpatterns = [
    url(r'^slack/$', SlackViews.SlackViewSet.as_view({'post': 'slash'}), name='hooks-slack-slash'),
]
