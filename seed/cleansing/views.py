from annoying.decorators import ajax_request
from django.contrib.auth.decorators import login_required
from seed.utils.api import api_endpoint

@api_endpoint
@ajax_request
@login_required
def get_cleansing_results(request):
    """
    Retrieve the details of the cleansing script.

    TODO: This code is a placeholder and will require the data to be loaded from either disk, redis, or postgres.
    At the moment I think that the data should be loaded from the redis database, since the cleansing is all or nothing,
    and that the cleansing will be running asynchronously.

    """

    ret = []

    result = {
        'row': 7,
        'column': 'building_area',
        'column_unmapped': 'bldg area',
        'type': 'Error',
        'description': 'field is not an integer'
    }
    ret.append(result)

    result = {
        'row': 15,
        'column': 'building_address',
        'column_unmapped': 'edifice address',
        'type': 'Warning',
        'description': 'building is located in the middle of the Indian ocean'
    }
    ret.append(result)

    return ret
