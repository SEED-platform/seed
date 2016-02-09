import datetime
import json
import logging

import requests
from dateutil import tz
from django.conf import settings

from seed.models import (
    Meter,
    TimeSeries,
)



_log = logging.getLogger(__name__)


def aggr_sum_metric(data, localtzone):
    '''
    aggregate monthly data kairos and push it to postgres. data represents the aggregate query
    '''

    headers = {'content-type': 'application/json'}

    url = settings.TSDB['query_url']

    data = json.dumps(data)

    r = requests.post(url, data=data, headers=headers)
    # length of output array. Should be 1 per group since it's monthly aggregation and we are querying only for one month

    if not 'queries' in r.json():
        return

    res = r.json()['queries'][0]['results']

    length = len(res)

    # Retrieve required values from array and call posgres insert function
    for num in range(0, length):
        if len(res[num]['tags']) > 0:
            res_tags = res[num]['tags']

            gb_bldg_canonical_id = res_tags['canonical_id'][0]
            gb_mtr_id = res_tags['custom_meter_id'][0]
            gb_energy_type_id = res_tags['energy_type_int'][0]

            resultarrlen = len(res[num]['values'])
            res_values = res[num]['values']

            for numv in range(0, resultarrlen):
                gb_timestamp = res_values[numv][0]
                gb_agg_reading = res_values[numv][1]

                timestamp = datetime.datetime.fromtimestamp(gb_timestamp / 1000.0, tz.gettz(localtzone))
                tsMonthStart = timestamp.replace(day=1).replace(hour=0).replace(minute=0).replace(second=0)
                tsMonthEnd = timestamp.replace(hour=23).replace(minute=59).replace(second=59)

                mlist = [1, 3, 5, 7, 8, 10, 12]
                if tsMonthEnd.month in mlist:
                    tsMonthEnd = tsMonthEnd.replace(day=31)
                elif (tsMonthEnd.month == 2):
                    if (year % 100 != 0 and year % 4 == 0) or (year % 100 == 0 and year % 400 == 0):
                        tsMonthEnd = tsMonthEnd.replace(day=29)
                    else:
                        tsMonthEnd = tsMonthEnd.replace(day=28)
                else:
                    tsMonthEnd = tsMonthEnd.replace(day=30)

                # push data to postgres
                insert_into_postgres(localtzone, gb_bldg_canonical_id, gb_mtr_id, gb_energy_type_id, gb_timestamp,
                                     gb_agg_reading, tsMonthStart, tsMonthEnd)
            else:
                _log.info('End of internal for loop')
        else:
            _log.info('No data found for given timeperiod')
    else:
        _log.info('End of for loop')


# insert into postgres
def insert_into_postgres(localtzone, gb_bldg_canonical_id, gb_mtr_id, gb_energy_type_id, gb_timestamp, gb_agg_reading,
                         tsMonthStart, tsMonthEnd):
    # retrieve meter_id from seed_meter using buildingsnapshot_id, green_button_meter_id, energy_type
    res = Meter.objects.filter(custom_meter_id=gb_mtr_id, energy_type=gb_energy_type_id).select_related().filter(
        canonical_building=gb_bldg_canonical_id)

    # insert in seed_timeseries
    for row in res:
        mtr_id = row.id
        begintime = tsMonthStart.strftime("%Y-%m-%d %H:%M:%S%z")
        endtime = tsMonthEnd.strftime("%Y-%m-%d %H:%M:%S%z")

        ts = TimeSeries.objects.filter(begin_time=begintime, meter_id=mtr_id)

        if not ts:
            new_ts = TimeSeries(begin_time=begintime, end_time=endtime, reading=gb_agg_reading, meter_id=mtr_id)
            new_ts.save()
        else:
            _log.info(
                'Skipping for ' + str(mtr_id) + ' ts ' + datetime.datetime.fromtimestamp(gb_timestamp / 1000).strftime(
                    '%Y-%m-%d'))
    else:
        _log.info('Insertion Loop ended')
