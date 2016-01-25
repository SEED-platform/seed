# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author

How to map dataset attributes to CanonicalBuilding.

If the first element in the tuple is a callable, it will be passed
a model instance for that type of mapping (AssessedBuilding for
AssessedBuilding_to_CanonicalBuilding, etc.)
"""
from seed.utils.mapping import get_mappable_columns


# Keys are destination attributes in our model
# Values are expected data types so we can present reasonable approximations
# of validation in the frontend.

PortfolioRaw_to_BuildingSnapshot = (
    (u'property_id', u'pm_property_id'),
    (u'custom_property_id_1_-_id', u'custom_id_1'),
    (u'property_notes', u'property_notes'),
    (u'year_ending', u'year_ending'),
    (u'property_name', u'property_name'),
    (u'property_floor_area_bldg_park', u'gross_floor_area'),
    (u'address_line_1', u'address_line_1'),
    (u'address_line_2', u'address_line_2'),
    (u'city', u'city'),
    (u'postal_code', u'postal_code'),
    (u'county', u'district'),
    (u'year_built', u'year_built'),
    (u'energy_score', u'energy_score'),
    (u'generation_date', u'generation_date'),
    (u'release_date', u'release_date'),
    (u'state_province', u'state_province'),
    (u'site_eui', u'site_eui'),
    (u'propertys_portfolio_manager_account_holder', u'owner'),
    (u'propertys_portfolio_manager_account_holder_email', u'owner_email'),
    (u'weather_normalized_site_eui', u'site_eui_weather_normalized'),
    (u'weather_normalized_source_eui', u'source_eui_weather_normalized'),
    (u'energy_alerts', u'energy_alerts'),
    (u'third_party_certification', u'building_certification'),
)

BuildingSnapshot_to_BuildingSnapshot = tuple([(k, k) for k in get_mappable_columns()])
