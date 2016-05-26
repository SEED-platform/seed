from django.conf.urls import url

from seed.bluesky import views


urlpatterns = [
    url(r'^properties/?$', views.get_properties, name='properties'),
    url(r'^property/(?P<property_pk>\d+)/?$', views.get_property, name='property-detail'),
    url(r'^lots/?$', views.get_taxlots, name='lots'),
    url(r'^lot/(?P<taxlot_pk>\d+)/?$', views.get_taxlot, name='lot-detail'),
]
