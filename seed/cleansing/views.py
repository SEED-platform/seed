# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import csv
from django.contrib.auth.decorators import login_required
from seed.utils.cache import get_cache_raw, get_cache
from django.http import HttpResponse
from seed.cleansing.models import Cleansing
from seed.decorators import ajax_request
from seed.utils.api import api_endpoint
from seed.decorators import get_prog_key


# TODO The API is returning on both a POST and GET. Make sure to authenticate.


@api_endpoint
@ajax_request
@login_required
def get_cleansing_results(request):
    """
    Retrieve the details of the cleansing script.
    """

    import_file_id = request.GET.get('import_file_id')
    cleansing_results = get_cache_raw(Cleansing.cache_key(import_file_id))

    return {
        'status': 'success',
        'message': 'Cleansing complete',
        'progress': 100,
        'data': cleansing_results
    }


@api_endpoint
@ajax_request
@login_required
def get_progress(request):
    """
    Return the progress of the cleansing.
    """

    import_file_id = request.GET.get('import_file_id')
    return get_cache(get_prog_key('get_progress', import_file_id))['progress']


@api_endpoint
@ajax_request
@login_required
def get_csv(request):
    """
    Download a csv of the results.
    """

    import_file_id = request.GET.get('import_file_id')
    cleansing_results = get_cache_raw(Cleansing.cache_key(import_file_id))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Data Cleansing Results.csv"'

    writer = csv.writer(response)
    writer.writerow(['Address Line 1', 'PM Property ID', 'Tax Lot ID', 'Custom ID', 'Field',
                     'Error Message', 'Severity'])
    for row in cleansing_results:
        for result in row['cleansing_results']:
            writer.writerow([
                row['address_line_1'],
                row['pm_property_id'],
                row['tax_lot_id'],
                row['custom_id_1'],
                result['formatted_field'],
                result['detailed_message'],
                result['severity']
            ])

    return response
