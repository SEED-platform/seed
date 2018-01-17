from django.core.serializers.json import DjangoJSONEncoder
from quantityfield import ureg

from rest_framework import serializers


def to_raw_magnitude(obj):
    return "{:.2f}".format(obj.magnitude)


class PintJSONEncoder(DjangoJSONEncoder):
    """
    Converts pint Quantity objects for Angular's benefit.
    # TODO handle unit conversion on the server per-org
    """

    def default(self, obj):
        if isinstance(obj, ureg.Quantity):
            return to_raw_magnitude(obj)
        return super(PintJSONEncoder, self).default(obj)


class PintQuantitySerializerField(serializers.Field):
    """
    Serialize the Pint quantity for use in rest framework
    """

    def to_representation(self, obj):
        return obj.magnitude

    def to_internal_value(self, data):
        # get the field off of the database table to get the base units
        field = self.root.Meta.model._meta.get_field(self.field_name)

        try:
            data = data * ureg(field.base_units)
        except ValueError:
            data = None

        return data
