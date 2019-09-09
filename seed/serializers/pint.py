"""
Collects the various utility functions for doing a last-moment collapse of the
Pint-aware values/columns to raw floats before sending them out over the API.
Generally this collapsing relies on having access to the organization, since
that's where the display preference lives.
"""

import re

from builtins import str
from django.core.serializers.json import DjangoJSONEncoder
from quantityfield import ureg
from rest_framework import serializers

AREA_DIMENSIONALITY = '[length] ** 2'
EUI_DIMENSIONALITY = '[mass] / [time] ** 3'

AREA_DEFAULT_UNITS = 'ft**2'
EUI_DEFAULT_UNITS = 'kBtu/ft**2/year'


def to_raw_magnitude(obj):
    return "{:.2f}".format(obj.magnitude)


def get_dimensionality(quantity_object):
    return str(quantity_object.dimensionality)


def collapse_unit(org, x):
    """
    Collapse a Quantity object present down to a straight Float, per the
    preferences of the organization supplied (or the base units). Generally
    used to hide the fact of Quantities from Angular.
    """
    # make extensible / field name agnostic by just branching on the dimensionality
    # and not the field name (eg. 'gross_floor_area') ... the dimensionality gets
    # enforced separately by the django pint column type
    pint_specs = {
        EUI_DIMENSIONALITY: org.display_units_eui or EUI_DEFAULT_UNITS,
        AREA_DIMENSIONALITY: org.display_units_area or AREA_DEFAULT_UNITS
    }

    if isinstance(x, ureg.Quantity):
        dimensionality = get_dimensionality(x)
        pint_spec = pint_specs[dimensionality]
        converted_value = x.to(pint_spec).magnitude
        return round(converted_value, org.display_significant_figures)
    elif isinstance(x, list):
        # recurse out to collapse a dict for eg. the `related` key that
        # contains properties when the pt_dict is for a taxlot and vice-versa
        return [apply_display_unit_preferences(org, y) for y in x]
    else:
        return x


def apply_display_unit_preferences(org, pt_dict):
    """
    take a dict of property/taxlot data just before it gets sent off across the
    API and collapse any Quantity objects present down to a straight float, per
    the organization preferences.
    """
    converted_dict = {k: collapse_unit(org, v) for k, v in pt_dict.items()}

    return converted_dict


def pretty_units(quantity):
    """
    hack; can lose it when Pint gets something like a "{:~U}" format code
    see https://github.com/hgrecco/pint/pull/231
    """
    return '{:~P}'.format(quantity).split(' ')[1]


def pretty_units_from_spec(unit_spec):
    quantity = 0 * ureg(unit_spec)  # doesn't matter what the number is
    return pretty_units(quantity)


def add_pint_unit_suffix(organization, column):
    """
    transforms the displayName coming from `Column.retrieve_all` to add known
    units where applicable,  eg. 'Gross Floor Area' to 'Gross Floor Area (sq.
    ft.)', using the organization's unit preferences.
    """

    def format_column_name(column_name, unit_spec):
        display_units = pretty_units_from_spec(unit_spec)
        # strip the suffix; shouldn't have to do this when we've swapped over
        # the columns. The mere presence of a unit suffix will tell us in the UI
        # that this is a Pint-aware column
        stripped_name = re.sub(r' \(pint\)$', '', column_name, flags=re.IGNORECASE)
        return stripped_name + ' ({})'.format(display_units)

    try:
        if column['dataType'] == 'area':
            column['displayName'] = format_column_name(
                column['displayName'], organization.display_units_area)
        elif column['dataType'] == 'eui':
            column['displayName'] = format_column_name(
                column['displayName'], organization.display_units_eui)
    except KeyError:
        pass  # no transform needed if we can't detect dataType, nbd
    return column


class PintJSONEncoder(DjangoJSONEncoder):
    """
    Converts pint Quantity objects for Angular's benefit.
    # TODO handle unit conversion on the server per-org
    """

    def default(self, obj):
        if isinstance(obj, ureg.Quantity):
            return to_raw_magnitude(obj)
        return super().default(obj)


class PintQuantitySerializerField(serializers.Field):
    """
    Serialize the Pint quantity for use in rest framework
    """

    def to_representation(self, obj):
        if isinstance(obj, ureg.Quantity):
            if isinstance(self.root.instance, list):
                state = self.root.instance[0] if self.root.instance else None
            else:
                state = self.root.instance
            try:
                org = state.organization
            except AttributeError:
                org = state.state.organization
            value = collapse_unit(org, obj)
            return value
        else:
            return obj

    def to_internal_value(self, data):
        # get the field off of the database table to get the base units
        field = self.root.Meta.model._meta.get_field(self.field_name)

        try:
            data = float(data) * ureg(field.base_units)
        except ValueError:
            data = None

        return data
