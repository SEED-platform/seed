from django.conf.urls import patterns, url

urlpatterns = patterns(
    'seed.cleansing.views',
    url(r'results/', 'get_cleansing_results', name='get_cleansing_results'),
    url(r'progress/', 'get_progress', name='get_progress'),
    url(r'download/', 'get_csv', name='get_csv'),
)



