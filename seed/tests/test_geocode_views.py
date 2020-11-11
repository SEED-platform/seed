# !/usr/bin/env python
# encoding: utf-8

import ast

from django.urls import reverse

from django.test import TestCase

from seed.landing.models import SEEDUser as User

from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState

from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotViewFactory
)

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
        self.tax_lot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org)

    def test_geocode_endpoint_base_with_prepopulated_lat_long_no_api_request(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['latitude'] = 39.765251
        property_details['longitude'] = -104.986138

        property = PropertyState(**property_details)
        property.save()

        property_view = self.property_view_factory.get_property_view(state=property)

        post_params = {
            'property_view_ids': [property_view.id],
            'taxlot_view_ids': []
        }

        url = reverse('api:v3:geocode-geocode-by-ids') + '?organization_id=%s' % self.org.pk
        self.client.post(url, post_params)

        refreshed_property = PropertyState.objects.get(pk=property.id)

        self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_property))

    def test_geocode_confidence_summary_returns_summary_dictionary(self):
        property_none_details = self.property_state_factory.get_details()
        property_none_details["organization_id"] = self.org.id
        property_none = PropertyState(**property_none_details)
        property_none.save()

        property_none_view = self.property_view_factory.get_property_view(state=property_none)

        property_high_details = self.property_state_factory.get_details()
        property_high_details["organization_id"] = self.org.id
        property_high_details["geocoding_confidence"] = "High (P1AAA)"
        property_high = PropertyState(**property_high_details)
        property_high.save()

        property_high_view = self.property_view_factory.get_property_view(state=property_high)

        property_low_details = self.property_state_factory.get_details()
        property_low_details["organization_id"] = self.org.id
        property_low_details["geocoding_confidence"] = "Low (P1CCC)"
        property_low = PropertyState(**property_low_details)
        property_low.save()

        property_low_view = self.property_view_factory.get_property_view(state=property_low)

        property_manual_details = self.property_state_factory.get_details()
        property_manual_details["organization_id"] = self.org.id
        property_manual_details["geocoding_confidence"] = "Manually geocoded (N/A)"
        property_manual = PropertyState(**property_manual_details)
        property_manual.save()

        property_manual_view = self.property_view_factory.get_property_view(state=property_manual)

        property_missing_details = self.property_state_factory.get_details()
        property_missing_details["organization_id"] = self.org.id
        property_missing_details["geocoding_confidence"] = "Missing address components (N/A)"
        property_missing = PropertyState(**property_missing_details)
        property_missing.save()

        property_missing_view = self.property_view_factory.get_property_view(state=property_missing)

        tax_lot_none_details = self.tax_lot_state_factory.get_details()
        tax_lot_none_details["organization_id"] = self.org.id
        tax_lot_none = TaxLotState(**tax_lot_none_details)
        tax_lot_none.save()

        taxlot_none_view = self.taxlot_view_factory.get_taxlot_view(state=tax_lot_none)

        tax_lot_high_details = self.tax_lot_state_factory.get_details()
        tax_lot_high_details["organization_id"] = self.org.id
        tax_lot_high_details["geocoding_confidence"] = "High (P1AAA)"
        tax_lot_high = TaxLotState(**tax_lot_high_details)
        tax_lot_high.save()

        taxlot_high_view = self.taxlot_view_factory.get_taxlot_view(state=tax_lot_high)

        tax_lot_low_details = self.tax_lot_state_factory.get_details()
        tax_lot_low_details["organization_id"] = self.org.id
        tax_lot_low_details["geocoding_confidence"] = "Low (P1CCC)"
        tax_lot_low = TaxLotState(**tax_lot_low_details)
        tax_lot_low.save()

        taxlot_low_view = self.taxlot_view_factory.get_taxlot_view(state=tax_lot_low)

        tax_lot_manual_details = self.tax_lot_state_factory.get_details()
        tax_lot_manual_details["organization_id"] = self.org.id
        tax_lot_manual_details["geocoding_confidence"] = "Manually geocoded (N/A)"
        tax_lot_manual = TaxLotState(**tax_lot_manual_details)
        tax_lot_manual.save()

        taxlot_manual_view = self.taxlot_view_factory.get_taxlot_view(state=tax_lot_manual)

        tax_lot_missing_details = self.tax_lot_state_factory.get_details()
        tax_lot_missing_details["organization_id"] = self.org.id
        tax_lot_missing_details["geocoding_confidence"] = "Missing address components (N/A)"
        tax_lot_missing = TaxLotState(**tax_lot_missing_details)
        tax_lot_missing.save()

        taxlot_missing_view = self.taxlot_view_factory.get_taxlot_view(state=tax_lot_missing)

        url = reverse('api:v3:geocode-confidence-summary')
        post_params = {
            'organization_id': self.org.pk,
            'property_view_ids': [
                property_none_view.id,
                property_high_view.id,
                property_low_view.id,
                property_manual_view.id,
                property_missing_view.id
            ],
            'taxlot_view_ids': [
                taxlot_none_view.id,
                taxlot_high_view.id,
                taxlot_low_view.id,
                taxlot_manual_view.id,
                taxlot_missing_view.id
            ]
        }

        result = self.client.post(url, post_params)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))
        expectation = {
            "properties": {
                "not_geocoded": 1,
                "high_confidence": 1,
                "low_confidence": 1,
                "manual": 1,
                "missing_address_components": 1
            },
            "tax_lots": {
                "not_geocoded": 1,
                "high_confidence": 1,
                "low_confidence": 1,
                "manual": 1,
                "missing_address_components": 1
            }
        }

        self.assertEqual(result_dict, expectation)

    def test_api_key_endpoint_returns_true_or_false_if_org_has_api_key(self):
        url = reverse("api:v3:organizations-geocode-api-key-exists", args=[self.org.pk])
        post_params_false = {'organization_id': self.org.pk}
        false_result = self.client.get(url, post_params_false)

        self.assertEqual(b'false', false_result.content)

        org_with_key, _, _ = create_organization(self.user)
        org_with_key.mapquest_api_key = "somekey"
        org_with_key.save()

        url = reverse("api:v3:organizations-geocode-api-key-exists", args=[org_with_key.id])
        post_params_true = {'organization_id': org_with_key.id}
        true_result = self.client.get(url, post_params_true)

        self.assertEqual(b'true', true_result.content)

    def test_geocode_enabled_endpoint(self):

        # try with geocoding turned on
        org_with_key, _, _ = create_organization(self.user)
        org_with_key.geocoding_enabled = True
        org_with_key.save()

        url = reverse("api:v3:organizations-geocoding-enabled", args=[org_with_key.id])
        post_params_true = {'organization_id': org_with_key.id}
        true_result = self.client.get(url, post_params_true)

        self.assertEqual(b'true', true_result.content)

        # try with geocoding turned off
        org_without_key, _, _ = create_organization(self.user)
        org_without_key.geocoding_enabled = False
        org_without_key.save()

        url = reverse("api:v3:organizations-geocoding-enabled", args=[org_without_key.id])
        post_params_false = {'organization_id': org_without_key.id}
        false_result = self.client.get(url, post_params_false)

        self.assertEqual(b'false', false_result.content)
