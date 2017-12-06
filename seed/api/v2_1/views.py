# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

# Imports from Standard Library

import pint
import xmltodict
from django.db.models import Q
from django_filters import CharFilter, DateFilter
from django_filters.rest_framework import FilterSet
from django.http import JsonResponse
from rest_framework.decorators import api_view

from seed.models import (
    PropertyState,
    PropertyView,
)
from seed.pmintegration.manager import PortfolioManagerImport
from seed.serializers.properties import PropertyViewAsStateSerializer
from seed.utils.viewsets import (
    SEEDOrgReadOnlyModelViewSet
)


class PropertyViewFilterSet(FilterSet):
    """
    Advanced filtering for PropertyView sets version 2.1.
    """
    address_line_1 = CharFilter(name="state__address_line_1", lookup_expr='contains')
    identifier = CharFilter(method='identifier_filter')
    cycle_start = DateFilter(name='cycle__start', lookup_expr='lte')
    cycle_end = DateFilter(name='cycle__end', lookup_expr='gte')

    class Meta:
        model = PropertyView
        fields = ['identifier', 'address_line_1', 'cycle', 'property', 'cycle_start', 'cycle_end']

    def identifier_filter(self, queryset, name, value):
        address_line_1 = Q(state__address_line_1__contains=value)
        jurisdiction_property_id = Q(state__jurisdiction_property_id__iexact=value)
        custom_id_1 = Q(state__custom_id_1__iexact=value)
        pm_property_id = Q(state__pm_property_id=value)
        query = (
            address_line_1 |
            jurisdiction_property_id |
            custom_id_1 |
            pm_property_id
        )
        return queryset.filter(query)


class PropertyViewSetV21(SEEDOrgReadOnlyModelViewSet):
    """
    Properties API Endpoint

        Returns::
            {
                'status': 'success',
                'properties': [
                    {
                        'id': Property primary key,
                        'campus': property is a campus,
                        'parent_property': dict of associated parent property
                        'labels': list of associated label ids
                    }
                ]
            }


    retrieve:
        Return a Property instance by pk if it is within specified org.

    list:
        Return all Properties available to user through specified org.
    """
    serializer_class = PropertyViewAsStateSerializer
    model = PropertyView
    data_name = "properties"
    filter_class = PropertyViewFilterSet
    orgfilter = 'property__organization_id'


ATTRIBUTES_TO_PROCESS = [
    'national_median_site_energy_use',
    'site_energy_use',
    'source_energy_use',
    'site_eui',
    'source_eui'
]


def normalize_attribute(attribute_object):
    u_registry = pint.UnitRegistry()
    if '@uom' in attribute_object and '#text' in attribute_object:
        # this is the correct expected path for unit-based attributes
        string_value = attribute_object['#text']
        try:
            float_value = float(string_value)
        except ValueError:
            return {'status': 'error', 'message': 'Could not cast value to float: \"%s\"' % string_value}
        original_unit_string = attribute_object['@uom']
        if original_unit_string == u'kBtu':
            converted_value = float_value * 3.0
            return {'status': 'success', 'value': converted_value, 'units': str(u_registry.meter)}
        elif original_unit_string == u'kBtu/ft²':
            converted_value = float_value * 3.0
            return {'status': 'success', 'value': converted_value, 'units': str(u_registry.meter)}
        elif original_unit_string == u'Metric Tons CO2e':
            converted_value = float_value * 3.0
            return {'status': 'success', 'value': converted_value, 'units': str(u_registry.meter)}
        elif original_unit_string == u'kgCO2e/ft²':
            converted_value = float_value * 3.0
            return {'status': 'success', 'value': converted_value, 'units': str(u_registry.meter)}
        else:
            return {'status': 'error', 'message': 'Unsupported units string: \"%s\"' % original_unit_string}


@api_view(['POST'])
def pm_integration_get_templates(request):
    if 'email' not in request.data:
        return JsonResponse('Invalid call to PM worker: missing email for PM account')
    if 'username' not in request.data:
        return JsonResponse('Invalid call to PM worker: missing username for PM account')
    if 'password' not in request.data:
        return JsonResponse('Invalid call to PM worker: missing password for PM account')
    email = request.data['email']
    username = request.data['username']
    password = request.data['password']
    pm = PortfolioManagerImport(email, username, password)
    possible_templates = pm.get_list_of_report_templates()
    return JsonResponse({'status': 'success', 'templates': possible_templates})  # TODO: Could just return ['name']s...
    # print("  Index  |  Template Report Name  ")
    # print("---------|------------------------")
    # for i, t in enumerate(possible_templates):
    #     print("  %s  |  %s  " % (str(i).ljust(5), t['name']))
    # selection = raw_input("\nEnter an Index to download the report: ")
    # try:
    #     s_id = int(selection)
    # except ValueError:
    #     raise Exception("Invalid Selection; aborting.")
    # if 0 <= s_id < len(possible_templates):
    #     selected_template = possible_templates[s_id]
    # else:
    #     raise Exception("Invalid Selection; aborting.")


@api_view(['POST'])
def pm_integration_worker(request):
    if 'email' not in request.data:
        return JsonResponse('Invalid call to PM worker: missing email for PM account')
    if 'username' not in request.data:
        return JsonResponse('Invalid call to PM worker: missing username for PM account')
    if 'password' not in request.data:
        return JsonResponse('Invalid call to PM worker: missing password for PM account')
    if 'template_name' not in request.data:
        return JsonResponse('Invalid call to PM worker: missing template_name for PM account')
    email = request.data['email']
    username = request.data['username']
    password = request.data['password']
    template_name = request.data['template_name']
    pm = PortfolioManagerImport(email, username, password)
    possible_templates = pm.get_list_of_report_templates()
    selected_template = [p for p in possible_templates if p['name'] == template_name][0]  # TODO: Shouldn't need this
    content = pm.generate_and_download_template_report(selected_template)
    try:
        content_object = xmltodict.parse(content)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Malformed XML response from template download'}, status=500)
    success = True
    if 'report' not in content_object:
        success = False
    if 'informationAndMetrics' not in content_object['report']:
        success = False
    if 'row' not in content_object['report']['informationAndMetrics']:
        success = False
    if not success:
        return JsonResponse({'status': 'error',
                             'message': 'Template XML response was properly formatted but was missing expected keys.'},
                            status=500)
    properties = content_object['report']['informationAndMetrics']['row']

    # now we need to actually process each property
    # if we find a match we should update it, if we don't we should create it
    # then we should assign/update property values, possibly from this list?
    #  energy_score
    #  site_eui
    #  generation_date
    #  release_date
    #  source_eui_weather_normalized
    #  site_eui_weather_normalized
    #  source_eui
    #  energy_alerts
    #  space_alerts
    #  building_certification
    for prop in properties:
        seed_property_match = None

        # first try to match by pm property id if the PM report includes it
        if 'property_id' in prop:
            this_property_pm_id = prop['property_id']
            try:
                seed_property_match = PropertyState.objects.get(pm_property_id=this_property_pm_id)
                prop['MATCHED'] = 'Matched via pm_property_id'
            except PropertyState.DoesNotExist:
                seed_property_match = None

        # second try to match by address/city/state if the PM report includes it
        if not seed_property_match:
            if all(attr in prop for attr in ['address_1', 'city', 'state_province']):
                this_property_address_one = prop['address_1']
                this_property_city = prop['city']
                this_property_state = prop['state_province']
                try:
                    seed_property_match = PropertyState.objects.get(
                        address_line_1__iexact=this_property_address_one,
                        city__iexact=this_property_city,
                        state__iexact=this_property_state
                    )
                    prop['MATCHED'] = 'Matched via address/city/state'
                except PropertyState.DoesNotExist:
                    seed_property_match = None

        # if we didn't match then we need to create a new one
        if not seed_property_match:
            prop['MATCHED'] = 'NO! need to create new property'

        # either way at this point we should have a property, existing or new
        # so now we should process the attributes
        processed_attributes = {}
        for attribute_to_check in ATTRIBUTES_TO_PROCESS:
            if attribute_to_check in prop:
                found_attribute = prop[attribute_to_check]
                if isinstance(found_attribute, dict):
                    if found_attribute['#text']:
                        if found_attribute['#text'] == 'Not Available':
                            processed_attributes[attribute_to_check] = 'Requested variable blank/unavailable on PM'
                        else:
                            updated_attribute = normalize_attribute(found_attribute)
                            processed_attributes[attribute_to_check] = updated_attribute
                    else:
                        processed_attributes[attribute_to_check] = 'Malformed attribute did not have #text field'
                else:
                    pass  # nothing for now

        prop['PROCESSED'] = processed_attributes

    return JsonResponse({'status': 'success', 'properties': properties})
