"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import itertools
import json
import logging

from django.db.models import F

# Imports from Django
from django.http import JsonResponse
from rest_framework import status

# Local Imports
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    VIEW_LIST,
    VIEW_LIST_PROPERTY,
    Column,
    ColumnListProfile,
    ColumnListProfileColumn,
    PropertyView,
    TaxLotProperty,
    TaxLotView,
)
from seed.serializers.pint import apply_display_unit_preferences

logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.ERROR, datefmt="%Y-%m-%d %H:%M:%S")


def get_changed_fields(old, new):
    """Return changed fields as json string"""
    changed_fields, changed_extra_data, previous_data = diffupdate(old, new)

    if "id" in changed_fields:
        changed_fields.remove("id")
        del previous_data["id"]

    if "pk" in changed_fields:
        changed_fields.remove("pk")
        del previous_data["pk"]

    if not (changed_fields or changed_extra_data):
        return None, None
    else:
        return json.dumps({"regular_fields": changed_fields, "extra_data_fields": changed_extra_data}), previous_data


def diffupdate(old, new):
    """Returns lists of fields changed"""
    changed_fields = []
    changed_extra_data = []
    previous_data = {}

    for k, v in new.items():
        if old.get(k, None) != v or k not in old:
            changed_fields.append(k)
            previous_data[k] = old.get(k, None)

    if "extra_data" in changed_fields:
        changed_fields.remove("extra_data")
        changed_extra_data, _, previous_extra_data = diffupdate(old["extra_data"], new["extra_data"])
        previous_data["extra_data"] = previous_extra_data

    return changed_fields, changed_extra_data, previous_data


def update_result_with_master(result, master):
    result["changed_fields"] = master.get("changed_fields", None) if master else None
    result["date_edited"] = master.get("date_edited", None) if master else None
    result["source"] = master.get("source", None) if master else None
    result["filename"] = master.get("filename", None) if master else None
    return result


def unique(lol):
    """Calculate unique elements in a list of lists."""
    return sorted(set(itertools.chain.from_iterable(lol)))


def pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, pair):
    # TODO: validate against organization_id, make sure cycle_ids are the same

    try:
        property_view = PropertyView.objects.get(pk=property_id)
    except PropertyView.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": f"property view with id {property_id} does not exist"}, status=status.HTTP_404_NOT_FOUND
        )
    try:
        taxlot_view = TaxLotView.objects.get(pk=taxlot_id)
    except TaxLotView.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": f"tax lot view with id {taxlot_id} does not exist"}, status=status.HTTP_404_NOT_FOUND
        )

    pv_cycle = property_view.cycle_id
    tv_cycle = taxlot_view.cycle_id

    if pv_cycle != tv_cycle:
        return JsonResponse(
            {"status": "error", "message": "Cycle mismatch between PropertyView and TaxLotView"}, status=status.HTTP_400_BAD_REQUEST
        )

    if pair:
        string = "pair"

        if TaxLotProperty.objects.filter(property_view_id=property_id, taxlot_view_id=taxlot_id).exists():
            return JsonResponse({"status": "success", "message": f"taxlot {taxlot_id} and property {property_id} are already {string}ed"})
        TaxLotProperty(primary=True, cycle_id=pv_cycle, property_view_id=property_id, taxlot_view_id=taxlot_id).save()

        success = True
    else:
        string = "unpair"

        if not TaxLotProperty.objects.filter(property_view_id=property_id, taxlot_view_id=taxlot_id).exists():
            return JsonResponse({"status": "success", "message": f"taxlot {taxlot_id} and property {property_id} are already {string}ed"})
        TaxLotProperty.objects.filter(property_view_id=property_id, taxlot_view_id=taxlot_id).delete()

        success = True

    if success:
        return JsonResponse({"status": "success", "message": f"taxlot {taxlot_id} and property {property_id} are now {string}ed"})
    else:
        return JsonResponse(
            {"status": "error", "message": f"Could not {string} because reasons, maybe bad organization id={organization_id}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def properties_across_cycles(org_id, ali, profile_id, cycle_ids=[]):
    # Identify column preferences to be used to scope fields/values
    columns_from_database = Column.retrieve_all(org_id, "property", False)

    if profile_id == -1:
        show_columns = list(Column.objects.filter(organization_id=org_id).values_list("id", flat=True))
    else:
        try:
            profile = ColumnListProfile.objects.get(
                organization_id=org_id, id=profile_id, profile_location=VIEW_LIST, inventory_type=VIEW_LIST_PROPERTY
            )
            show_columns = list(
                ColumnListProfileColumn.objects.filter(column_list_profile_id=profile.id).values_list("column_id", flat=True)
            )
        except ColumnListProfile.DoesNotExist:
            show_columns = None

    results = {}
    for cycle_id in cycle_ids:
        # get -Views for this Cycle
        property_views = (
            PropertyView.objects.select_related("property", "state", "cycle")
            .filter(
                property__organization_id=org_id,
                cycle_id=cycle_id,
                property__access_level_instance__lft__gte=ali.lft,
                property__access_level_instance__rgt__lte=ali.rgt,
            )
            .order_by("id")
        )

        related_results = TaxLotProperty.serialize(property_views, show_columns, columns_from_database)

        org = Organization.objects.get(pk=org_id)
        unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

        results[cycle_id] = unit_collapsed_results

    return results


def properties_across_cycles_with_filters(org_id, user_ali, cycle_ids=[], query_dict={}, columns=[]):
    # get relevant views
    views_list = PropertyView.objects.select_related("property", "state", "cycle").filter(
        property__organization_id=org_id,
        cycle_id__in=cycle_ids,
        property__access_level_instance__lft__gte=user_ali.lft,
        property__access_level_instance__rgt__lte=user_ali.rgt,
    )
    views_list = _serialize_views(views_list, columns, org_id)

    # group by cycle
    results = {cycle_id: [] for cycle_id in cycle_ids}
    for view in views_list:
        cycle_id = view["cycle_id"]
        del view["cycle_id"]
        results[cycle_id].append(view)

    return results


def _serialize_views(views_list, columns, org_id):
    org = Organization.objects.get(pk=org_id)

    # build annotations
    annotations = {}
    values_list = ["id", "cycle_id"]  # django readable names
    returned_name = ["id", "cycle_id"]  # actual api names
    for column in columns:
        if column.is_extra_data:
            anno_value = F("state__extra_data__" + column.column_name)
        elif column.derived_column:
            anno_value = F("state__derived_data__" + column.column_name)
        else:
            anno_value = F("state__" + column.column_name)

        name = f"{column.column_name.replace(' ', '_')}_{column.id}"  # django readable name
        annotations[name] = anno_value
        values_list.append(name)
        returned_name.append(f"{column.column_name}_{column.id}")

    # use api names and add units
    views_list = views_list.annotate(**annotations).values_list(*values_list)
    views_list = [dict(zip(returned_name, view)) for view in views_list]  # replace django readable name with api name
    views_list = [apply_display_unit_preferences(org, view) for view in views_list]

    return views_list


def properties_across_cycles_with_columns(org_id, show_columns=[], cycle_ids=[]):
    # Identify column preferences to be used to scope fields/values
    columns_from_database = Column.retrieve_all(org_id, "property", False)

    results = {}
    for cycle_id in cycle_ids:
        # get -Views for this Cycle
        property_views = (
            PropertyView.objects.select_related("property", "state", "cycle")
            .filter(property__organization_id=org_id, cycle_id=cycle_id)
            .order_by("id")
        )

        related_results = TaxLotProperty.serialize(property_views, show_columns, columns_from_database)

        org = Organization.objects.get(pk=org_id)
        unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

        results[cycle_id] = unit_collapsed_results

    return results
