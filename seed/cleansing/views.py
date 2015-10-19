import csv
from annoying.decorators import ajax_request
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from seed.cleansing.models import Cleansing
from seed.utils.api import api_endpoint

# TODO The API is returning on both a POST and GET. Make sure to authenticate.


@api_endpoint
@ajax_request
@login_required
def get_cleansing_results(request):
    """
    Retrieve the details of the cleansing script.
    """

    import_file_id = request.GET.get('import_file_id')
    cleansing_results = cache.get(Cleansing.cache_key(import_file_id), [])
    for i, row in enumerate(cleansing_results):
        for j, result in enumerate(row['cleansing_results']):
            if result['field'] in Cleansing.ASSESSOR_FIELDS_BY_COLUMN:
                result['field'] = Cleansing.ASSESSOR_FIELDS_BY_COLUMN[result['field']]['title']

    return cleansing_results


@api_endpoint
@ajax_request
@login_required
def get_progress(request):
    """
    Return the progress of the cleansing.
    """

    import_file_id = request.GET.get('import_file_id')
    return cache.get(get_prog_key(import_file_id))


@api_endpoint
@ajax_request
@login_required
def get_csv(request):
    """
    Download a csv of the results.
    """

    import_file_id = request.GET.get('import_file_id')
    cleansing_results = cache.get(Cleansing.cache_key(import_file_id), [])
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Data Cleansing Results.csv"'

    writer = csv.writer(response)
    writer.writerow(['Address Line 1', 'PM Property ID', 'Tax Lot ID', 'Custom ID', 'Field',
                     'Error Message', 'Severity'])
    for row in cleansing_results:
        for result in row['cleansing_results']:
            field = result['field']
            if field in Cleansing.ASSESSOR_FIELDS_BY_COLUMN:
                field = Cleansing.ASSESSOR_FIELDS_BY_COLUMN[field]['title']
            writer.writerow([row['address_line_1'], row['pm_property_id'], row['tax_lot_id'], row['custom_id_1'], field,
                             result['message'], result['severity']])

    return response
