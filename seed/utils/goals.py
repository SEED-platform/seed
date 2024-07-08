# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db.models import Case, F, FloatField, IntegerField, Sum, Value, When
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce
from quantityfield.units import ureg

from seed.models import GoalNote, PropertyView
from seed.serializers.pint import collapse_unit


def get_eui_expression(goal):
    """
    goal.eui_column is designed to only accept columns of data_type=eui (columns like site_eui, or source_eui)
    however the user may choose to use an extra_data column that has been typed on the frontend as 'eui'.
    This frontend change does not affect the db, and extra_data fields are stored as JSON objects
    extra_data = {Name: value} where value can be any type.

    This function dynamically finds the highest priority eui column and sets its type to Integer
    """
    priority = []

    # Iterate through the columns in priority order
    for eui_column in goal.eui_columns():
        if eui_column.is_extra_data:
            eui_column_expression = extra_data_expression(eui_column, None)
        else:
            eui_column_expression = Cast(F(f"state__{eui_column.column_name}"), output_field=FloatField())

        priority.append(eui_column_expression)

    # default value
    priority.append(Value(None, output_field=FloatField()))
    # Coalesce to pick the first non-null value
    eui_expression = Coalesce(*priority, output_field=FloatField())

    return eui_expression


def get_area_expression(goal):
    """
    goal.area_column is designed to only accept columns of data_type=area (columns like gross_foor_area)
    however the user may choose to use an extra_data column that has been typed on the frontend as 'area'.
    This frontend change does not effect the db, and extra_data fields are stored as JSON objects
    extra_data = {Name: value} where value can be any type.
    """
    if goal.area_column.is_extra_data:
        return extra_data_expression(goal.area_column, 0.0)
    else:
        return Cast(F(f"state__{goal.area_column.column_name}"), output_field=IntegerField())


def extra_data_expression(column, default_value):
    """
    extra_data is a JSON object and could be any data type. Convert to float if possible
    """
    return Case(
        # use regex to determine if value can be converted to a number (int or float)
        When(
            **{f"state__extra_data__{column.column_name}__regex": r"^\d+(\.\d+)?$"},
            then=Cast(KeyTextTransform(column.column_name, "state__extra_data"), output_field=FloatField()),
        ),
        default=Value(default_value),
        output_field=FloatField(),
    )


def percentage_difference(a, b):
    """
    Returns 100 - percentage
    """
    if not a or not b:
        return None
    return int((a - b) / a * 100) or 0


def percentage(a, b):
    """
    Returns percentage
    """
    if not a or not b:
        return None
    return int(b / a * 100) or 0


def get_or_create_goal_notes(goal):
    """
    If properties are added after goals have been created they wont have goal_notes. Create those goal_notes.
    """

    # Find properties without goal_notes
    property_ids = goal.properties().exclude(goalnote__goal=goal).values_list("id", flat=True)
    new_goal_notes = [GoalNote(goal=goal, property_id=id) for id in property_ids]
    GoalNote.objects.bulk_create(new_goal_notes)


def get_portfolio_summary(org, goal):
    """
    Gets a Portfolio Summary dictionary given a goal
    """
    summary = {}

    for current, cycle in enumerate([goal.baseline_cycle, goal.current_cycle]):
        # Return all properties
        property_views = PropertyView.objects.select_related("property", "state").filter(
            property__organization_id=org.id,
            cycle_id=cycle.id,
            property__access_level_instance__lft__gte=goal.access_level_instance.lft,
            property__access_level_instance__rgt__lte=goal.access_level_instance.rgt,
            property__goalnote__goal__id=goal.id,
        )
        # Shared area is area of all properties regardless of valid status
        property_views = property_views.annotate(area=get_area_expression(goal))
        if current:
            summary["total_properties"] = property_views.count()
            summary["shared_sqft"] = property_views.aggregate(shared_sqft=Sum("area"))["shared_sqft"]
            summary["total_passing"] = GoalNote.objects.filter(goal=goal, passed_checks=True).count()
            summary["total_new_or_acquired"] = GoalNote.objects.filter(goal=goal, new_or_acquired=True).count()

        # Remaining Calcs are restricted to passing checks and not new/acquired
        # use goal notes relation to properties to get valid properties views
        valid_property_ids = GoalNote.objects.filter(goal=goal, passed_checks=True, new_or_acquired=False).values_list(
            "property__id", flat=True
        )
        property_views = property_views.filter(property__id__in=valid_property_ids)

        # Create annotations for kbtu calcs. "eui" is based on goal column priority
        property_views = property_views.annotate(
            eui=get_eui_expression(goal),
        ).annotate(kbtu=F("eui") * F("area"))

        aggregated_data = property_views.aggregate(total_kbtu=Sum("kbtu"), total_sqft=Sum("area"))
        total_kbtu = aggregated_data["total_kbtu"]
        total_sqft = aggregated_data["total_sqft"]  # shared sqft

        if current:
            summary["passing_committed"] = percentage(goal.commitment_sqft, total_sqft)
            summary["passing_shared"] = percentage(summary["shared_sqft"], total_sqft)

        if total_kbtu:
            total_kbtu = int(total_kbtu)

        if total_kbtu is not None and total_sqft:
            # apply units for potential unit conversion (no org setting for type ktbu so it is ignored)
            total_sqft = total_sqft * ureg("ft**2")
            weighted_eui = total_kbtu * ureg("kBtu/year") / total_sqft
            weighted_eui = int(collapse_unit(org, weighted_eui))
        else:
            weighted_eui = None

        if total_sqft is not None:
            total_sqft = collapse_unit(org, total_sqft)

        cycle_type = "current" if current else "baseline"

        summary[cycle_type] = {
            "cycle_name": cycle.name,
            "total_sqft": total_sqft,
            "total_kbtu": total_kbtu,
            "weighted_eui": weighted_eui,
        }

    summary["sqft_change"] = percentage_difference(summary["current"]["total_sqft"], summary["baseline"]["total_sqft"])
    summary["eui_change"] = percentage_difference(summary["baseline"]["weighted_eui"], summary["current"]["weighted_eui"])

    return summary
