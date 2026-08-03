"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from seed.lib.superperms.orgs.models import Organization
from seed.models import VIEW_LIST, VIEW_LIST_TAXLOT, Column, ColumnListProfile, ColumnListProfileColumn, TaxLotProperty, TaxLotView
from seed.serializers.pint import apply_display_unit_preferences


def taxlots_across_cycles(org_id, ali, profile_id, cycle_ids=[]):
    # Identify column preferences to be used to scope fields/values
    columns_from_database = Column.retrieve_all(org_id, "taxlot", False)

    if profile_id == -1:
        show_columns = list(Column.objects.filter(organization_id=org_id).values_list("id", flat=True))
    else:
        try:
            profile = ColumnListProfile.objects.get(
                organization_id=org_id, id=profile_id, profile_location=VIEW_LIST, inventory_type=VIEW_LIST_TAXLOT
            )
            show_columns = list(
                ColumnListProfileColumn.objects.filter(column_list_profile_id=profile.id).values_list("column_id", flat=True)
            )
        except ColumnListProfile.DoesNotExist:
            show_columns = None

    # Normalize to ints up front so pre-initialized keys below always match the cycle_id
    # values looked up from the database later, regardless of what type the caller passed.
    cycle_ids = [int(cycle_id) for cycle_id in cycle_ids]
    results = {cycle_id: [] for cycle_id in cycle_ids}
    if not cycle_ids:
        return results

    # Fetch every TaxLotView across all requested cycles in a single query and run
    # TaxLotProperty.serialize() once for the whole batch, instead of once per cycle. The
    # previous per-cycle loop re-ran serialize()'s internal `__in` sub-queries and
    # re-fetched the (unchanging) organization row once per selected cycle - the more
    # cycles requested, the more redundant work was done for no benefit.
    taxlot_views = list(
        TaxLotView.objects.select_related("taxlot", "state", "cycle")
        .filter(
            taxlot__organization_id=org_id,
            cycle_id__in=cycle_ids,
            taxlot__access_level_instance__lft__gte=ali.lft,
            taxlot__access_level_instance__rgt__lte=ali.rgt,
        )
        .order_by("id")
    )
    cycle_id_by_view_id = {view.id: view.cycle_id for view in taxlot_views}

    related_results = TaxLotProperty.serialize(taxlot_views, show_columns, columns_from_database)

    org = Organization.objects.get(pk=org_id)
    for result in related_results:
        cycle_id = cycle_id_by_view_id[result["taxlot_view_id"]]
        results[cycle_id].append(apply_display_unit_preferences(org, result))

    return results
