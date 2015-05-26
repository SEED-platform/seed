"""
:copyright: (c) 2014 Building Energy Inc

This module describes how data is mapped from our ontology to Django Models.
The structure pulls out the read data from our espm-based MCM run
like follows:

espm['flat_schema'].keys() -> model.attr mapping

All fields found in the ontology, but not mentioned in this mapping
go into the ``extra_data`` attribute, which is a json field in Postgres.

"""
MAP = {
    # Could there be a better key for this?
    u'Property Id': u'pm_property_id',
    u'Property Name': u'property_name',
    u'Address 1': u'address_line_1',
    u'Address 2': u'address_line_2',
    u'City': u'city',
    u'County': u'district',
    u'City': u'city',
    u'Custom Property ID 1 - ID': u'custom_id_1',
    u'Postal Code': u'postal_code',
    u'State/Province': u'state_province',
    u'Property Floor Area (Buildings and Parking) (ft2)': (
        u'gross_floor_area'
    ),
    u'Year Built': u'year_built',
    u'Year Ending': u'year_ending',
    u'Energy Alerts': u'energy_alerts',
    u'ENERGY STAR Score': u'energy_score',
    u'Site EUI (kBtu/ft2)': u'site_eui',
    u'Source EUI (kBtu/ft2)': u'source_eui',
    u'Weather Normalized Site EUI (kBtu/ft2)': u'site_eui_weather_normalized',
    u'Weather Normalized Source EUI (kBtu/ft2)': (
        u'source_eui_weather_normalized'
    ),
    u'Generation Date': u'generation_date',
    u'Release Date': u'release_date',
}
