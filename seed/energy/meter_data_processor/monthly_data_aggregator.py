from django.db.models import Q
from seed.models import (
    Meter,
    CanonicalBuilding,
    TimeSeries,
)
from django.conf import settings
from django.core.cache import cache
from dateutil import tz

from celery import Celery
from celery import task 
import datetime
import time
import calendar
import requests
import json
import sys
import pytz
import logging
from pytz import timezone

LOCK_EXPIRE = 60 * 60 * 24 * 30 # Lock expires in 30 days

_log = logging.getLogger(__name__)

def datetime_to_timestamp(dt):
       return (dt - datetime.datetime(1970, 1, 1)).total_seconds()

def aggr_sum_metric(data, localtzone):
    '''
    aggregate monthly data kairos and push it to postgres. data represents the aggregate query
    '''

    headers = {'content-type': 'application/json'}

    url = settings.TSDB['query_url']

    data = json.dumps(data)

    r = requests.post(url, data=data, headers=headers)
    #length of output array. Should be 1 per group since it's monthly aggregation and we are querying only for one month

    if not 'queries' in r.json():
        return
    
    res = r.json()['queries'][0]['results']

    #Retrieve required values from array and call posgres insert function
	for idx_res, value_res in enumerate(res):
        if len(value_res['tags']) > 0:
            res_tags = value_res['tags']
        
            gb_bldg_canonical_id =  res_tags['canonical_id'][0]
            gb_mtr_id =  res_tags['custom_meter_id'][0]
            gb_energy_type_id =  res_tags['energy_type_int'][0]

            res_values = value_res['values']

            for idx_res_values, value_res_values in enumerate(res_values):
                gb_timestamp =  value_res_values[0]
                gb_agg_reading = value_res_values[1]

                timestamp = datetime.datetime.fromtimestamp(gb_timestamp/1000.0, tz.gettz(localtzone))
                tsMonthStart =  timestamp.replace(day=1).replace(hour=0).replace(minute=0).replace(second=0)
                tsMonthEnd = timestamp.replace(hour=23).replace(minute=59).replace(second=59)

                mlist = [1,3,5,7,8,10,12]
                if tsMonthEnd.month in mlist:
                    tsMonthEnd = tsMonthEnd.replace(day=31)
                elif (tsMonthEnd.month == 2):
                    if calendar.isleap(tsMonthEnd.year):
                        tsMonthEnd = tsMonthEnd.replace(day=29)
                    else:
                        tsMonthEnd = tsMonthEnd.replace(day=28)
                else:
                    tsMonthEnd = tsMonthEnd.replace(day=30)

                #push data to postgres
                insert_into_postgres(localtzone, gb_bldg_canonical_id, gb_mtr_id, gb_energy_type_id, gb_timestamp, gb_agg_reading, tsMonthStart, tsMonthEnd)
            else:
                _log.info('End of internal for loop')
        else:
            _log.info('No data found for given timeperiod')
    else:
        _log.info('End of for loop')

#insert into postgres
def insert_into_postgres(localtzone, gb_bldg_canonical_id, gb_mtr_id, gb_energy_type_id, gb_timestamp, gb_agg_reading, tsMonthStart, tsMonthEnd):
    #retrieve meter_id from seed_meter using buildingsnapshot_id, green_button_meter_id, energy_type
    res = Meter.objects.filter(custom_meter_id=gb_mtr_id, energy_type=gb_energy_type_id).select_related().filter(canonical_building=gb_bldg_canonical_id)

    #insert in seed_timeseries
    for row in res:
        mtr_id = row.id
        begintime = tsMonthStart.strftime("%Y-%m-%d %H:%M:%S%z")
        endtime = tsMonthEnd.strftime("%Y-%m-%d %H:%M:%S%z")

        ts = TimeSeries.objects.filter(begin_time=begintime, meter_id=mtr_id)

        if not ts:
            new_ts = TimeSeries(begin_time=begintime, end_time=endtime, reading=gb_agg_reading, meter_id=mtr_id)
            new_ts.save()
        else:
            _log.info('Skipping for '+str(mtr_id)+' ts '+datetime.datetime.fromtimestamp(gb_timestamp/1000).strftime('%Y-%m-%d'))
    else:
        _log.info('Insertion Loop ended')

@task(name='aggregate_monthly_data')
def aggregate_monthly_data(building_id=-1):
    '''
    If building_id is not -1, do immediate aggregate
    '''

    # Alwasy only one or none monthly aggregator is running
    lock_id = 'aggregator_monthly_lock'
    acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)

    if building_id == -1:
        if not acquire_lock():
            _log.info('Another monthly aggregator is running')
            return

    localtzone = settings.LOCAL_TIMEZONE

    _log.info('Starting Aggregation')
    #find out last month's start and end timestamps
    monthlist = [1,3,5,7,8,10,12]
    today = datetime.datetime.today()
    #last month
    if today.month == 1:
        lastmonth = today.replace(year=(today.year - 1))
        lastmonth = lastmonth.replace(month=12)
    else:
        lastmonth = today.replace(month = (today.month - 1))

    #first day of last month
    firstDayOfLastMonth = lastmonth.replace(day=1).replace(hour=0).replace(minute=0).replace(second=0).replace(microsecond=0)

    #last day of the month
    if lastmonth.month in monthlist:
        lastDayOfLastMonth = lastmonth.replace(day=31)
    elif (lastmonth.month == 2) and (lastmonth.year%4 !=0):
        lastDayOfLastMonth = lastmonth.replace(day=28)
    elif (lastmonth.month == 2) and (lastmonth.year%4 ==0):
        lastDayOfLastMonth = lastmonth.replace(day=29)
    else:
        lastDayOfLastMonth = lastmonth.replace(day=30)
    lastDayOfLastMonth = lastDayOfLastMonth.replace(hour=23).replace(minute=59).replace(second=59).replace(microsecond=999999)

    #timestamps
    tsMonthStart = datetime_to_timestamp(firstDayOfLastMonth) * 1000
    tsMonthEnd = datetime_to_timestamp(lastDayOfLastMonth) * 1000

	#KairosDB query body
    query_body = {}
    query_body['start_absolute'] = 1230768000000 #Jan 01, 2009. An early enough time stamp
    query_body['end_absolute'] = tsMonthEnd
    query_body['metrics'] = []
    
    metric = {}
    metric['tags'] = {}
    metric['name'] = str(settings.TSDB['measurement'])    
    
    aggregator = {}
    aggregator['name'] = 'sum'
    aggregator['align_sampling'] = True
    aggregator_sampling = {}
    aggregator_sampling['value'] = 1
    aggregator_sampling['unit'] = 'months'
    aggregator['sampling'] = aggregator_sampling
    aggregators = []
    aggregators.append(aggregator)
    metric['aggregators'] = aggregators
    
    group_by = {};
    group_by['name'] = 'tag'
    group_by['tags'] = ['enerty_type','canonical_id','custom_meter_id','interval']
    group_bys = []
    group_bys.append(group_by)
    metric['group_by'] = group_bys
        
    query_body['metrics'].append(metric)
    
    # direct aggregation called by analyzer
    if building_id>0:
        query_body['metrics'][0]['tags']['canonical_id'] = str(building_id)
        return aggr_sum_metric(query_body, localtzone)
    # direct call end

    insert_ts_tag_array = []
    for x in range(1,32):
        insert_ts_tag_array.append(lastDayOfLastMonth.strftime('%m')+'/'+str(x)+'/'+lastDayOfLastMonth.strftime('%Y'))

    #kairos aggregation query
    query_body['metrics'][0]['tags']['canonical_id'] = [str(insert_ts_tag_array[0]), str(insert_ts_tag_array[1]), str(insert_ts_tag_array[2]), str(insert_ts_tag_array[3]), str(insert_ts_tag_array[4]), str(insert_ts_tag_array[5]), str(insert_ts_tag_array[6]), str(insert_ts_tag_array[7]), str(insert_ts_tag_array[8]), str(insert_ts_tag_array[9]), str(insert_ts_tag_array[10]), str(insert_ts_tag_array[11]), str(insert_ts_tag_array[12]), str(insert_ts_tag_array[13]), str(insert_ts_tag_array[14]), str(insert_ts_tag_array[15]), str(insert_ts_tag_array[16]), str(insert_ts_tag_array[17]), str(insert_ts_tag_array[18]), str(insert_ts_tag_array[19]), str(insert_ts_tag_array[20]), str(insert_ts_tag_array[21]), str(insert_ts_tag_array[22]), str(insert_ts_tag_array[23]), str(insert_ts_tag_array[24]), str(insert_ts_tag_array[25]), str(insert_ts_tag_array[26]), str(insert_ts_tag_array[27]), str(insert_ts_tag_array[28]), str(insert_ts_tag_array[29]), str(insert_ts_tag_array[30])]

    #aggregate data using the agg_query
    aggr_sum_metric(agg_query, localtzone)

    if building_id == -1:
        release_lock()
        _log.info('monthly aggregator lock released')
