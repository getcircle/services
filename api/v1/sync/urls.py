from django.conf.urls import url

from . import views


urlpatterns = [
    url(
        r'^start/$',
        views.SyncViewSet.as_view({'post': 'start'}),
        name='public-api-v1-sync-start',
    ),
    url(
        r'^users/$',
        views.SyncViewSet.as_view({'post': 'sync_users'}),
        name='public-api-v1-sync-users',
    ),
    url(
        r'^groups/$',
        views.SyncViewSet.as_view({'post': 'sync_groups'}),
        name='public-api-v1-sync-groups',
    ),
    url(
        r'^complete/$',
        views.SyncViewSet.as_view({'post': 'complete'}),
        name='public-api-v1-sync-complete',
    ),
    url(
        r'^check/$',
        views.SyncViewSet.as_view({'post': 'check'}),
        name='public-api-v1-sync-check',
    ),
]
