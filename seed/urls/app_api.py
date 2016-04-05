from django.conf.urls import patterns, url

urlpatterns = patterns(
    'seed.views.app_api',
    url(
        r'^overview_portfolio/$',
        'overview_portfolio',
        name='overview_portfolio'
    ),
)
