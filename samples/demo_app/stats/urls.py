from django.conf.urls import patterns, url


urlpatterns = patterns(
    'stats.views',
    url(r'^$', 'stats', name='stats'),
)
