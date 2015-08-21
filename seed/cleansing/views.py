from annoying.decorators import ajax_request
from django.contrib.auth.decorators import login_required
from seed.utils.api import api_endpoint
from django.core.cache import cache

# TODO The API is returning on both a POST and GET. Make sure to authenticate.


@api_endpoint
@ajax_request
@login_required
def get_cleansing_results(request):
    """
    Retrieve the details of the cleansing script.
    """

    import_file_id = request.GET.get('import_file_id')
    ret = cache.get("cleansing_results__%s" % import_file_id)
    if ret is None:
        return {}

    return ret


@api_endpoint
@ajax_request
@login_required
def get_progress(request):
    result = {
        'progress_key': 'some_random_key',
        'progress': 50
    }

    return result
