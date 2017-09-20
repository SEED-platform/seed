from django.core.serializers.json import DjangoJSONEncoder
from quantityfield import ureg


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
