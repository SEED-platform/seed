# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

# Imports from Standard Library
import itertools
import json

# Imports from Django
from django.http import JsonResponse
from rest_framework import status

# Local Imports
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Column,
    ColumnListProfile,
    ColumnListProfileColumn,
    PropertyView,
    TaxLotProperty,
    TaxLotView,
    VIEW_LIST,
    VIEW_LIST_PROPERTY,
)
from seed.serializers.pint import apply_display_unit_preferences


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


def properties_across_cycles(org_id, profile_id, cycle_ids=[]):
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
            .filter(property__organization_id=org_id, cycle_id=cycle_id) \
            .order_by('id')

        related_results = TaxLotProperty.get_related(property_views, show_columns, columns_from_database)

        org = Organization.objects.get(pk=org_id)
        unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

        results[cycle_id] = unit_collapsed_results

    return results
