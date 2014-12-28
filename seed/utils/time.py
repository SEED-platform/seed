import dateutil


def convert_datestr(datestr):
    """Converts dates like `12/31/2010` into datetime objects."""
    try:
        return dateutil.parser.parse(datestr)
    except (TypeError, ValueError):
        return None


def convert_to_js_timestamp(timestamp):
    """converts a django/python datetime object to milliseconds since epoch"""
    if timestamp:
        return int(timestamp.strftime("%s")) * 1000
    return None
