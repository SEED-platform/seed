from django.db.models import Q
from seed.models import (
    GreenButtonBatchRequestsInfo,
)

import logging
import time
import calendar
from datetime import date, timedelta, datetime

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from seed.energy.meter_data_processor.monthly_data_aggregator import aggr_sum_metric
from seed.energy.meter_data_processor import green_button_driver as driver
import green_button_data_analyser as analyser
from seed.energy.meter_data_processor import kairos_insert as db_insert

_log = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 60 * 24 * 30  # Lock expires in 30 days


def datetime_to_timestamp(dt):
    return (dt - datetime.datetime(1970, 1, 1)).total_seconds()


def increment_day(date_str):
    """
    Format of date_str is MM/DD/YYYY
    """

    if date_str == '' or date_str is None:
        newdate = date.today() - timedelta(1)
    else:
        t = time.strptime(date_str, '%m/%d/%Y')
        newdate = date(t.tm_year, t.tm_mon, t.tm_mday) + timedelta(1)

    return newdate.strftime('%m/%d/%Y')


@shared_task
def process_green_button_batch_request(row_id, url, subscription_id, building_id, time_type, date_pattern, min_date_para, min_date, max_date_para):
    today_date = date.today()
    today_str = today_date.strftime('%m/%d/%Y')

    yesterday = date.today() - timedelta(1)
    yesterday_str = yesterday.strftime('%m/%d/%Y')

    if time_type == 'date':
        last_datetime = datetime.strptime(min_date, date_pattern)
        last_date = last_datetime.date()

        if last_date > yesterday:
            _log.info('Green Button last date is beyond yesterday')
            return

        url = url + settings.GREEN_BUTTON_BATCH_URL_SYNTAX + subscription_id + "&" + min_date_para + "=" + min_date + "&" + max_date_para + "=" + yesterday_str
    elif time_type == 'timestamp':
        last_date = long(min_date)
        if last_date > yesterday:
            _log.info('Green Button last date is beyond yesterday')
            return

        yesterday_timestamp = str(calendar.timegm(time.strptime(yesterday_str, '%m/%d/%Y')))

        url = url + settings.GREEN_BUTTON_BATCH_URL_SYNTAX + subscription_id + "&" + min_date_para + "=" + min_date + "&" + max_date_para + "=" + str(yesterday)

    _log.info('Fetching url '+url)
    print url
    ts_data = driver.get_gb_data(url, building_id)

    _log.info('data fetched')

    if ts_data!=None:
        analyser.data_analyse(ts_data, 'GreenButton')

        _log.info('update db record: last_date=\''+today_str+'\' for id='+str(row_id))
        record = GreenButtonBatchRequestsInfo.objects.get(id=row_id)
        record.last_date = today_str
        record.save()


@shared_task
def green_button_task_runner():
    lock_id = 'green_button_batch_request_scheduler_lock'
    if not cache.add(lock_id, 'true', None):
        _log.info('last green_button_task_runner is not finished')
        print 'last green_button_task_runner is not finished'
        return

    record = GreenButtonBatchRequestsInfo.objects.filter(active='Y')
    if record:
        for gb_info in record:
            last_date_str = gb_info.last_date
            row_id = gb_info.id
            url = gb_info.url
            subscription_id = gb_info.subscription_id
            min_date_parameter = gb_info.min_date_parameter
            max_date_parameter = gb_info.max_date_parameter
            building_id = gb_info.building_id

            time_type = gb_info.time_type
            date_pattern = gb_info.date_pattern

            process_green_button_batch_request.delay(row_id, url, subscription_id, building_id, time_type, date_pattern, min_date_parameter, last_date_str, max_date_parameter)
    else:
        _log.info('No GreenButton record info found')

    cache.delete(lock_id)


@shared_task
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
    # find out last month's start and end timestamps
    monthlist = [1, 3, 5, 7, 8, 10, 12]
    today = datetime.datetime.today()
    # last month
    if today.month == 1:
        lastmonth = today.replace(year=(today.year - 1))
        lastmonth = lastmonth.replace(month=12)
    else:
        lastmonth = today.replace(month=(today.month - 1))

    # last day of the month
    if lastmonth.month in monthlist:
        lastDayOfLastMonth = lastmonth.replace(day=31)
    elif lastmonth.month == 2:
        if calendar.isleap(lastmonth.year):
            lastDayOfLastMonth = lastmonth.replace(day=29)
        else:
            lastDayOfLastMonth = lastmonth.replace(day=28)
    else:
        lastDayOfLastMonth = lastmonth.replace(day=30)
    lastDayOfLastMonth = lastDayOfLastMonth.replace(hour=23).replace(minute=59).replace(second=59).replace(
        microsecond=999999)

    # timestamps
    # tsMonthStart = datetime_to_timestamp(firstDayOfLastMonth) * 1000  # Not used
    tsMonthEnd = datetime_to_timestamp(lastDayOfLastMonth) * 1000

    # KairosDB query body
    query_body = {}
    query_body['start_absolute'] = 1230768000000  # Jan 01, 2009. An early enough time stamp
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

    group_by = {}
    group_by['name'] = 'tag'
    group_by['tags'] = ['enerty_type', 'canonical_id', 'custom_meter_id', 'interval']
    group_bys = []
    group_bys.append(group_by)
    metric['group_by'] = group_bys

    query_body['metrics'].append(metric)

    # direct aggregation called by analyzer
    if building_id > 0:
        query_body['metrics'][0]['tags']['canonical_id'] = str(building_id)
        return aggr_sum_metric(query_body, localtzone)
    # direct call end

    insert_ts_tag_array = []
    for x in range(1, 32):
        insert_ts_tag_array.append(
            lastDayOfLastMonth.strftime('%m') + '/' + str(x) + '/' + lastDayOfLastMonth.strftime('%Y'))

    # kairos aggregation query
    query_body['metrics'][0]['tags']['canonical_id'] = [str(insert_ts_tag_array[0]), str(insert_ts_tag_array[1]),
                                                        str(insert_ts_tag_array[2]), str(insert_ts_tag_array[3]),
                                                        str(insert_ts_tag_array[4]), str(insert_ts_tag_array[5]),
                                                        str(insert_ts_tag_array[6]), str(insert_ts_tag_array[7]),
                                                        str(insert_ts_tag_array[8]), str(insert_ts_tag_array[9]),
                                                        str(insert_ts_tag_array[10]), str(insert_ts_tag_array[11]),
                                                        str(insert_ts_tag_array[12]), str(insert_ts_tag_array[13]),
                                                        str(insert_ts_tag_array[14]), str(insert_ts_tag_array[15]),
                                                        str(insert_ts_tag_array[16]), str(insert_ts_tag_array[17]),
                                                        str(insert_ts_tag_array[18]), str(insert_ts_tag_array[19]),
                                                        str(insert_ts_tag_array[20]), str(insert_ts_tag_array[21]),
                                                        str(insert_ts_tag_array[22]), str(insert_ts_tag_array[23]),
                                                        str(insert_ts_tag_array[24]), str(insert_ts_tag_array[25]),
                                                        str(insert_ts_tag_array[26]), str(insert_ts_tag_array[27]),
                                                        str(insert_ts_tag_array[28]), str(insert_ts_tag_array[29]),
                                                        str(insert_ts_tag_array[30])]

    # aggregate data using the agg_query
    aggr_sum_metric(query_body, localtzone)

    if building_id == -1:
        release_lock()
        _log.info('monthly aggregator lock released')
