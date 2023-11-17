# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import itertools
import json

# Imports from Django
from django.http import JsonResponse
from rest_framework import status
from django.db.models import F, IntegerField, Sum, Value
from django.db.models.functions import Coalesce


# Local Imports
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    VIEW_LIST,
    VIEW_LIST_PROPERTY,
    Column,
    ColumnListProfile,
    ColumnListProfileColumn,
    Cycle,
    PropertyView,
    TaxLotProperty,
    TaxLotView
)
from seed.serializers.pint import apply_display_unit_preferences
from seed.utils.search import build_view_filters_and_sorts
import logging
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.ERROR,
    datefmt='%Y-%m-%d %H:%M:%S'
)


def get_changed_fields(old, new):
    """Return changed fields as json string"""
    changed_fields, changed_extra_data, previous_data = diffupdate(old, new)

    if 'id' in changed_fields:
        changed_fields.remove('id')
        del previous_data['id']

    if 'pk' in changed_fields:
        changed_fields.remove('pk')
        del previous_data['pk']

    if not (changed_fields or changed_extra_data):
        return None, None
    else:
        return json.dumps({
            'regular_fields': changed_fields,
            'extra_data_fields': changed_extra_data
        }), previous_data


def diffupdate(old, new):
    """Returns lists of fields changed"""
    changed_fields = []
    changed_extra_data = []
    previous_data = {}

    for k, v in new.items():
        if old.get(k, None) != v or k not in old:
            changed_fields.append(k)
            previous_data[k] = old.get(k, None)

    if 'extra_data' in changed_fields:
        changed_fields.remove('extra_data')
        changed_extra_data, _, previous_extra_data = diffupdate(old['extra_data'], new['extra_data'])
        previous_data['extra_data'] = previous_extra_data

    return changed_fields, changed_extra_data, previous_data


def update_result_with_master(result, master):
    result['changed_fields'] = master.get('changed_fields', None) if master else None
    result['date_edited'] = master.get('date_edited', None) if master else None
    result['source'] = master.get('source', None) if master else None
    result['filename'] = master.get('filename', None) if master else None
    return result


def unique(lol):
    """Calculate unique elements in a list of lists."""
    return sorted(set(itertools.chain.from_iterable(lol)))


def pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, pair):
    # TODO: validate against organization_id, make sure cycle_ids are the same

    try:
        property_view = PropertyView.objects.get(pk=property_id)
    except PropertyView.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'property view with id {} does not exist'.format(property_id)
        }, status=status.HTTP_404_NOT_FOUND)
    try:
        taxlot_view = TaxLotView.objects.get(pk=taxlot_id)
    except TaxLotView.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'tax lot view with id {} does not exist'.format(taxlot_id)
        }, status=status.HTTP_404_NOT_FOUND)

    pv_cycle = property_view.cycle_id
    tv_cycle = taxlot_view.cycle_id

    if pv_cycle != tv_cycle:
        return JsonResponse({
            'status': 'error',
            'message': 'Cycle mismatch between PropertyView and TaxLotView'
        }, status=status.HTTP_400_BAD_REQUEST)

    if pair:
        string = 'pair'

        if TaxLotProperty.objects.filter(property_view_id=property_id,
                                         taxlot_view_id=taxlot_id).exists():
            return JsonResponse({
                'status': 'success',
                'message': 'taxlot {} and property {} are already {}ed'.format(taxlot_id,
                                                                               property_id, string)
            })
        TaxLotProperty(primary=True, cycle_id=pv_cycle, property_view_id=property_id,
                       taxlot_view_id=taxlot_id) \
            .save()

        success = True
    else:
        string = 'unpair'

        if not TaxLotProperty.objects.filter(property_view_id=property_id,
                                             taxlot_view_id=taxlot_id).exists():
            return JsonResponse({
                'status': 'success',
                'message': 'taxlot {} and property {} are already {}ed'.format(taxlot_id,
                                                                               property_id, string)
            })
        TaxLotProperty.objects.filter(property_view_id=property_id, taxlot_view_id=taxlot_id) \
            .delete()

        success = True

    if success:
        return JsonResponse({
            'status': 'success',
            'message': 'taxlot {} and property {} are now {}ed'.format(taxlot_id, property_id,
                                                                       string)
        })
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Could not {} because reasons, maybe bad organization id={}'.format(string,
                                                                                           organization_id)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def properties_across_cycles(org_id, ali, profile_id, cycle_ids=[]):
    # Identify column preferences to be used to scope fields/values
    columns_from_database = Column.retrieve_all(org_id, 'property', False)

    if profile_id == -1:
        show_columns = list(Column.objects.filter(
            organization_id=org_id
        ).values_list('id', flat=True))
    else:
        try:
            profile = ColumnListProfile.objects.get(
                organization_id=org_id,
                id=profile_id,
                profile_location=VIEW_LIST,
                inventory_type=VIEW_LIST_PROPERTY
            )
            show_columns = list(ColumnListProfileColumn.objects.filter(
                column_list_profile_id=profile.id
            ).values_list('column_id', flat=True))
        except ColumnListProfile.DoesNotExist:
            show_columns = None

    results = {}
    for cycle_id in cycle_ids:
        # get -Views for this Cycle
        property_views = PropertyView.objects.select_related('property', 'state', 'cycle') \
            .filter(
                property__organization_id=org_id,
                cycle_id=cycle_id,
                property__access_level_instance__lft__gte=ali.lft,
                property__access_level_instance__rgt__lte=ali.rgt,
        ).order_by('id')

        related_results = TaxLotProperty.serialize(property_views, show_columns, columns_from_database)

        org = Organization.objects.get(pk=org_id)
        unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

        results[cycle_id] = unit_collapsed_results

    return results


def properties_across_cycles_with_filters(org_id, user_ali, cycle_ids=[], query_dict={}, column_ids=[]):
    # Identify column preferences to be used to scope fields/values
    columns_from_database = Column.retrieve_all(org_id, 'property', False)
    org = Organization.objects.get(pk=org_id)

    results = {cycle_id: [] for cycle_id in cycle_ids}
    property_views = _get_filter_group_views(org_id, cycle_ids, query_dict, user_ali)
    views_cycle_ids = [v.cycle_id for v in property_views]
    related_results = TaxLotProperty.serialize(property_views, column_ids, columns_from_database, include_related=False)
    unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

    for cycle_id, unit_collapsed_result in zip(views_cycle_ids, unit_collapsed_results):
        results[cycle_id].append(unit_collapsed_result)

    return results


# helper function for getting filtered properties
def _get_filter_group_views(org_id, cycles, query_dict, user_ali):

    columns = Column.retrieve_all(
        org_id=org_id,
        inventory_type='property',
        only_used=False,
        include_related=False
    )

    annotations = {}
    try:
        filters, annotations, order_by = build_view_filters_and_sorts(query_dict, columns, 'property')
    except Exception:
        return JsonResponse({
            'status': 'error',
            'message': 'error with filter group'
        }, status=status.HTTP_404_NOT_FOUND)

    views_list = (
        PropertyView.objects.select_related('property', 'state', 'cycle')
        .filter(
            property__organization_id=org_id,
            cycle__in=cycles,
            property__access_level_instance__lft__gte=user_ali.lft,
            property__access_level_instance__rgt__lte=user_ali.rgt,
        )
    )

    views_list = views_list.annotate(**annotations).filter(filters).order_by('id')

    return views_list


def properties_across_cycles_with_columns(org_id, show_columns=[], cycle_ids=[]):
    # Identify column preferences to be used to scope fields/values
    columns_from_database = Column.retrieve_all(org_id, 'property', False)

    results = {}
    for cycle_id in cycle_ids:
        # get -Views for this Cycle
        property_views = PropertyView.objects.select_related('property', 'state', 'cycle') \
            .filter(property__organization_id=org_id, cycle_id=cycle_id) \
            .order_by('id')

        related_results = TaxLotProperty.serialize(property_views, show_columns, columns_from_database)

        org = Organization.objects.get(pk=org_id)
        unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

        results[cycle_id] = unit_collapsed_results

    return results


def get_portfolio_summary(org_id, ali, cycle_ids):
    # Calculate Portfolio Summary stats for baseline and current cycles given ALI's
    cycles = Cycle.objects.filter(id__in=cycle_ids)
    cycle_lookup = {cycle.id: {'type': 'baseline' if cycle.id == cycle_ids[0] else 'current', 'name': cycle.name} for cycle in cycles}
    summary = {}
    for cycle_id in cycle_ids:
        # calcualte total_sqft, total_kbtu, and weighted_eui from property_views
        property_views = PropertyView.objects.select_related('property', 'state') \
            .filter(
                property__organization_id=org_id,
                cycle_id=cycle_id,
                property__access_level_instance__lft__gte=ali.lft,
                property__access_level_instance__rgt__lte=ali.rgt,
        )
        # create an order of prefered fields to perform the kbtu calculation
        prefered_fields = [
            F('state__source_eui_weather_normalized'),
            F('state__source_eui_modeled'),
            F('state__source_eui'),
        ]

        aggregated_data = property_views.aggregate(
            total_sqft=Sum('state__gross_floor_area'),
            total_kbtu=Sum(
                Coalesce(*prefered_fields) * F('state__gross_floor_area')
            )
        )

        def get_magnitude(key):
            value = aggregated_data.get(key, 0)
            return int(value.m) if value else 0
        
        total_sqft = get_magnitude('total_sqft')
        total_kbtu = get_magnitude('total_kbtu')
        weighted_eui = int(total_kbtu / total_sqft) if total_sqft else 0


        lookup = cycle_lookup[cycle_id]
        summary[lookup['type']] = {
            'cycle_name': lookup['name'],
            'total_sqft': total_sqft,
            'total_kbtu': total_kbtu,
            'weighted_eui': weighted_eui
        }
    
    def percentage(a,b):
        return int((a - b) / a * 100) if a != 0 else 0
    
    summary['sqft_change'] = percentage(summary['current']['total_sqft'], summary['baseline']['total_sqft'])
    summary['eui_change'] = percentage(summary['baseline']['weighted_eui'], summary['current']['weighted_eui'])

    return summary

def filter_views_by_property(org_id, ali, cycle_id, property_ids):
    # return property_views given a cycle and list of property_ids
    columns = Column.retrieve_all(org_id, 'property', False)
    show_columns = list(Column.objects.filter(organization_id=org_id).values_list('id', flat=True))

    property_views = PropertyView.objects.select_related('state').filter(
        property__access_level_instance__lft__gte=ali.lft,
        property__access_level_instance__rgt__lte=ali.rgt,
        cycle=cycle_id, 
        property__in=property_ids
    )
    related_results = TaxLotProperty.serialize(property_views, show_columns, columns)

    org = Organization.objects.get(pk=org_id)
    unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

    return unit_collapsed_results 