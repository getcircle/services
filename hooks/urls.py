from django.conf.urls import url

from .slack import views as SlackViews
from .email import views as EmailViews

urlpatterns = [
    url(r'^slack/$', SlackViews.SlackViewSet.as_view({'post': 'slash'}), name='hooks-slack-slash'),
    url(r'^email/$', EmailViews.ProcessEmailView.as_view(), name='hooks-email'),
]
