"""
Collects the various utility functions for doing a last-moment collapse of the
Pint-aware values/columns to raw floats before sending them out over the API.
Generally this collapsing relies on having access to the organization, since
that's where the display preference lives.
"""

from django.core.serializers.json import DjangoJSONEncoder
from quantityfield import ureg


def to_raw_magnitude(obj):
    return "{:.2f}".format(obj.magnitude)


def apply_display_unit_preferences(org_id, properties_or_taxlots):
    """
    """
    return properties_or_taxlots


def add_pint_unit_suffix(organization, column):
    """
    transforms the displayName coming from `Column.retrieve_all` to add known
    units where applicable,  eg. 'Gross Floor Area' to 'Gross Floor Area (sq.
    ft.)', using the organization's unit preferences.
    """
    try:
        if column['dataType'] == "area":
            column['displayName'] += " (" + organization.display_units_area + ")"
        elif column['dataType'] == "eui":
            column['displayName'] += " (" + organization.display_units_eui + ")"
    except KeyError:
        pass # no transform needed if we can't detect dataType, nbd
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
