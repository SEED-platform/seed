from annoying.decorators import ajax_request
from django.contrib.auth.decorators import login_required
from seed.utils.api import api_endpoint
from django.core.cache import cache

from seed.cleansing.models import Cleansing

# TODO The API is returning on both a POST and GET. Make sure to authenticate.


@api_endpoint
@ajax_request
@login_required
def get_cleansing_results(request):
    """
    Retrieve the details of the cleansing script.
    """

    import_file_id = request.GET.get('import_file_id')

    return cache.get(Cleansing.cache_key(import_file_id), [])


@api_endpoint
@ajax_request
@login_required
def get_progress(request):
    """
    Return the progress of the cleansing.
    """

    import_file_id = request.GET.get('import_file_id')
    return cache.get(get_prog_key(import_file_id))
