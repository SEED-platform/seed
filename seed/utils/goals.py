"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import math

from django.db.models import Case, F, FloatField, IntegerField, Prefetch, Sum, Value, When
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce
from quantityfield.units import ureg

from seed.models import Goal, GoalNote, Property, PropertyView
from seed.serializers.pint import collapse_unit
from seed.utils.generic import get_int


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
    goal.area_column is designed to only accept columns of data_type=area (columns like gross_floor_area)
    however the user may choose to use an extra_data column that has been typed on the frontend as 'area'.
    This frontend change does not affect the db, and extra_data fields are stored as JSON objects
    extra_data = {Name: value} where value can be any type.
    """
    if goal.area_column.is_extra_data:
        return extra_data_expression(goal.area_column, 0.0)
    else:
        return Cast(F(f"state__{goal.area_column.column_name}"), output_field=IntegerField())


def get_column_expression(column):
    """
    retrieves an expression to be used in annotation to return a specific columns value.

    goal.area_column is designed to only accept columns of data_type=area (columns like gross_floor_area)
    however the user may choose to use an extra_data column that has been typed on the frontend as 'area'.
    This frontend change does not affect the db, and extra_data fields are stored as JSON objects
    extra_data = {Name: value} where value can be any type.
    """
    if column.is_extra_data:
        return extra_data_expression(column, 0.0)
    else:
        return Cast(F(f"state__{column.column_name}"), output_field=IntegerField())


def get_eui_value(property_state, goal):
    """
    Return the eui value for a given property and goal
    """
    property_view = PropertyView.objects.filter(state__id=property_state.id).annotate(eui_value=get_eui_expression(goal)).first()
    return property_view.eui_value


def get_area_value(property_state, goal):
    """
    Return the area value for a given property and goal
    """
    property_view = (
        PropertyView.objects.filter(state__id=property_state.id).annotate(area_value=get_column_expression(goal.area_column)).first()
    )
    return property_view.area_value


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
    Returns 100 minus percentage
    """
    if not a or b is None:
        return None
    value = round(((a - b) / a) * 100)
    return None if math.isnan(value) else value


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
    transaction_goal = goal.type == "transaction"

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
        property_views = property_views.annotate(area=get_column_expression(goal.area_column))
        if current:
            summary["total_properties"] = property_views.count()
            summary["shared_sqft"] = property_views.aggregate(shared_sqft=Sum("area"))["shared_sqft"]
            summary["total_passing"] = GoalNote.objects.filter(goal=goal, passed_checks=True).count()
            summary["total_new_or_acquired"] = GoalNote.objects.filter(goal=goal, new_or_acquired=True).count()

        # Remaining calculations are restricted to passing check
        # New builds in the baseline year will be excluded from calculations
        # use goal notes relation to properties to get valid properties views
        goal_notes = GoalNote.objects.filter(goal=goal)
        new_property_ids = goal_notes.filter(new_or_acquired=True).values_list("property__id", flat=True)
        valid_property_ids = goal_notes.filter(passed_checks=True).values_list("property__id", flat=True)
        property_views = property_views.filter(property__id__in=valid_property_ids).exclude(
            cycle=goal.baseline_cycle, property__id__in=new_property_ids
        )

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

        key = "current" if current else "baseline"

        summary[f"{key}_cycle_name"] = cycle.name
        summary[f"{key}_total_sqft"] = total_sqft
        summary[f"{key}_total_kbtu"] = total_kbtu
        summary[f"{key}_weighted_eui"] = weighted_eui

        if transaction_goal:
            set_transaction_summary_cycle_data(property_views, summary, key, goal, total_kbtu)

    summary["sqft_change"] = percentage_difference(summary["current_total_sqft"], summary["baseline_total_sqft"])
    summary["eui_change"] = percentage_difference(summary["baseline_weighted_eui"], summary["current_weighted_eui"])

    if transaction_goal:
        set_transaction_summary_data(summary)

    return summary


def set_transaction_summary_cycle_data(property_views, summary, key, goal, total_kbtu):
    try:
        property_views = property_views.annotate(transactions=get_column_expression(goal.transactions_column))
        total_transactions = property_views.aggregate(total_transactions=Sum("transactions"))["total_transactions"]
    except Exception:
        total_transactions = None

    summary[f"{key}_total_transactions"] = round(total_transactions) if total_transactions is not None else None
    # hardcoded to always be kBtu/year
    summary[f"{key}_weighted_eui_t"] = round(total_kbtu / total_transactions) if total_transactions else None


def set_transaction_summary_data(summary):
    summary["transactions_change"] = percentage_difference(summary["current_total_transactions"], summary["baseline_total_transactions"])
    summary["eui_t_change"] = percentage_difference(summary["baseline_weighted_eui_t"], summary["current_weighted_eui_t"])


def get_state_pairs(property_ids, goal_id):
    """Given a list of property ids, return a dictionary containing baseline and current states"""
    # Prefetch PropertyView objects
    try:
        goal = Goal.objects.get(id=goal_id)
    except Goal.DoesNotExist:
        return []

    property_views = PropertyView.objects.filter(cycle__in=[goal.baseline_cycle, goal.current_cycle], property__in=property_ids)
    prefetch = Prefetch("views", queryset=property_views, to_attr="prefetched_views")

    # Fetch properties and related PropertyView objects
    qs = Property.objects.filter(id__in=property_ids).prefetch_related(prefetch)

    state_pairs = []
    for property in qs:
        # find related view from prefetched views
        baseline_view = next((pv for pv in property.prefetched_views if pv.cycle == goal.baseline_cycle), None)
        current_view = next((pv for pv in property.prefetched_views if pv.cycle == goal.current_cycle), None)

        baseline_state = baseline_view.state if baseline_view else None
        current_state = current_view.state if current_view else None

        state_pairs.append({"property": property, "baseline": baseline_state, "current": current_state})

    return state_pairs


def set_transaction_data(goal, prop, p1, p2, key1, key2):
    transaction_column = f"{goal.transactions_column.column_name}_{goal.transactions_column.id}"
    p1_transactions = get_int(p1.get(transaction_column))
    p2_transactions = get_int(p2.get(transaction_column))

    prop[f"{key1}_transactions"] = p1_transactions
    prop[f"{key2}_transactions"] = p2_transactions
    prop[f"{key1}_eui_t"] = get_eui_t(prop, key1, p1_transactions)
    prop[f"{key2}_eui_t"] = get_eui_t(prop, key2, p2_transactions)
    prop["transactions_change"] = percentage_difference(prop["current_transactions"], prop["baseline_transactions"])
    prop["eui_t_change"] = percentage_difference(prop["current_eui_t"], prop["baseline_eui_t"])

    return prop


def get_eui_t(prop, key, transactions):
    kbtu = prop.get(f"{key}_kbtu")
    if kbtu is None or not transactions:
        return None

    return round(kbtu / transactions) if prop else None


def combine_properties(p1, p2):
    if not p2:
        return p1
    combined = p1.copy()
    for key, value in p2.items():
        if value is not None:
            combined[key] = value
    return combined


def get_preferred(prop, columns):
    if not prop:
        return
    for col in columns:
        quantity = get_int(prop[col])
        if quantity is not None:
            return quantity


def get_kbtu(prop, key):
    if prop[f"{key}_sqft"] is not None and prop[f"{key}_eui"] is not None:
        return round(prop[f"{key}_sqft"] * prop[f"{key}_eui"])
