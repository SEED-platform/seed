# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

# Local Imports
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Column,
    ColumnListSetting,
    ColumnListSettingColumn,
    TaxLotProperty,
    TaxLotView,
    VIEW_LIST,
    VIEW_LIST_TAXLOT,
)
from seed.serializers.pint import apply_display_unit_preferences


def taxlots_across_cycles(org_id, profile_id, cycle_ids=[]):
    # Identify column preferences to be used to scope fields/values
    columns_from_database = Column.retrieve_all(org_id, 'taxlot', False)

    if profile_id == -1:
        show_columns = list(Column.objects.filter(
            organization_id=org_id
        ).values_list('id', flat=True))
    else:
        try:
            profile = ColumnListSetting.objects.get(
                organization_id=org_id,
                id=profile_id,
                settings_location=VIEW_LIST,
                inventory_type=VIEW_LIST_TAXLOT
            )
            show_columns = list(ColumnListSettingColumn.objects.filter(
                column_list_setting_id=profile.id
            ).values_list('column_id', flat=True))
        except ColumnListSetting.DoesNotExist:
            show_columns = None

    results = {}
    for cycle_id in cycle_ids:
        # get -Views for this Cycle
        taxlot_views = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
            .filter(taxlot__organization_id=org_id, cycle_id=cycle_id) \
            .order_by('id')

        related_results = TaxLotProperty.get_related(taxlot_views, show_columns, columns_from_database)

        org = Organization.objects.get(pk=org_id)
        unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

        results[cycle_id] = unit_collapsed_results

    return results
