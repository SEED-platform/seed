# !/usr/bin/env python
# encoding: utf-8

from django.core.urlresolvers import reverse

from django.test import TestCase

from seed.landing.models import SEEDUser as User

from seed.models.properties import PropertyState

from seed.test_helpers.fake import FakePropertyStateFactory

from seed.utils.geocode import long_lat_wkt
from seed.utils.organizations import create_organization


class GeocodeViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def test_geocode_endpoint_base_with_prepopulated_lat_long_no_api_request(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['latitude'] = 39.765251
        property_details['longitude'] = -104.986138

        property = PropertyState(**property_details)
        property.save()

        url = reverse('api:v2:geocode-geocode-by-ids')
        post_params = {
            'organization_id': self.org.pk,
            'property_ids': [property.id],
            'taxlot_ids': []
        }

        self.client.post(url, post_params)

        refreshed_property = PropertyState.objects.get(pk=property.id)

        self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_property))
