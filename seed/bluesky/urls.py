from django.conf.urls import url

from seed.bluesky import views


urlpatterns = [
    url(r'^properties/$', views.get_properties, name='properties'),
    url(r'^property/(?P<property_pk>\d+)/$', views.get_property, name='property-detail'),
    url(r'^lots/$', views.get_taxlots, name='lots'),
    url(r'^lot/(?P<taxlot_pk>\d+)/$', views.get_taxlot, name='lot-detail'),
    url(r'^cycles/$', views.get_cycles, name='cycles'),
    url(r'^property-columns/$', views.get_property_columns, name='property-columns'),
    url(r'^taxlot-columns/$', views.get_taxlot_columns, name='taxlot-columns'),
]
