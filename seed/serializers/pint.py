"""
Collects the various utility functions for doing a last-moment collapse of the
Pint-aware values/columns to raw floats before sending them out over the API.
Generally this collapsing relies on having access to the organization, since
that's where the display preference lives.
"""

import re
from django.core.serializers.json import DjangoJSONEncoder
from quantityfield import ureg

AREA_DIMENSIONALITY = '[length] ** 2'
EUI_DIMENSIONALITY = '[mass] / [time] ** 3'

AREA_DEFAULT_UNITS = 'ft**2'
EUI_DEFAULT_UNITS = 'kBtu/ft**2/year'

SIGNIFICANT_FIGURES = 2


def to_raw_magnitude(obj):
    return "{:.2f}".format(obj.magnitude)


def get_dimensionality(quantity_object):
    return str(quantity_object.dimensionality)


def apply_display_unit_preferences(org, pt_dict):
    """
    take a dict of property/taxlot data just before it gets sent off across the
    API and collapse any Quantity objects present down to a straight float, per
    the organization preferences.
    """

    # make extensible / field name agnostic by just branching on the dimensionality
    # and not the field name (eg. 'gross_floor_area') ... the dimensionality gets
    # enforced separately by the django pint column type
    pint_specs = {
        EUI_DIMENSIONALITY: org.display_units_eui or EUI_DEFAULT_UNITS,
        AREA_DIMENSIONALITY: org.display_units_area or AREA_DEFAULT_UNITS
    }

    def collapse_unit(x):
        if isinstance(x, ureg.Quantity):
            dimensionality = get_dimensionality(x)
            pint_spec = pint_specs[dimensionality]
            converted_value = x.to(pint_spec).magnitude
            return round(converted_value, SIGNIFICANT_FIGURES)
        elif isinstance(x, list):
            # recurse for eg. the `related` key that contains properties
            # when the pt_dict is for a taxlot and vice-versa
            return [apply_display_unit_preferences(org, y) for y in x]
        else:
            return x

    converted_dict = {k: collapse_unit(v) for k, v in pt_dict.iteritems()}

    return converted_dict


def pretty_units(quantity):
    """
    hack; can lose it when Pint gets something like a "{:~U}" format code
    see https://github.com/hgrecco/pint/pull/231
    """
    return u"{:~P}".format(quantity).split(" ")[1]


def pretty_units_from_spec(unit_spec):
    quantity = 0 * ureg(unit_spec) # doesn't matter what the number is
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
        stripped_name = re.sub(' \(pint\)$', '', column_name, flags=re.IGNORECASE)
        return stripped_name + u" ({})".format(display_units)

    try:
        if column['dataType'] == "area":
            column['displayName'] = \
                format_column_name(column['displayName'], organization.display_units_area)
        elif column['dataType'] == "eui":
            column['displayName'] = \
                format_column_name(column['displayName'], organization.display_units_eui)
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
        return super(PintJSONEncoder, self).default(obj)
