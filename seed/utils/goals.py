# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db.models import Case, F, FloatField, IntegerField, Value, When
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce


def get_eui_expression(goal):
    """
    goal.eui_columnx is designed to only accept columns of data_type=eui (columns like site_eui, or source_eui)
    however the user may choose to use an extra_data column that has been typed on the frontend as 'eui'.
    This frontend change does not effect the db, and extra_data fields are stored as JSON objects
    extra_data = {Name: value} where value can be any type.

    This function dynamically finds the highest priority eui column and sets its type to Integer
    """
    priority = []

    # Iterate through the columns in priority order
    for eui_column in goal.eui_columns():
        if eui_column.is_extra_data:
            eui_column_expression = extra_data_expression(eui_column, None)
        else:
            eui_column_expression = Cast(F(f'state__{eui_column.column_name}'), output_field=FloatField())

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
        return Cast(F(f'state__{goal.area_column.column_name}'), output_field=IntegerField())


def extra_data_expression(column, default_value):
    """
    extra_data is a JSON object and could be any data type. Convert to float if possible
    """
    return Case(
        # use regex to determine if value can be converted to a number (int or float)
        When(**{f'state__extra_data__{column.column_name}__regex': r'^\d+(\.\d+)?$'},
             then=Cast(KeyTextTransform(column.column_name, 'state__extra_data'), output_field=FloatField())),
        default=Value(default_value),
        output_field=FloatField()
    )
