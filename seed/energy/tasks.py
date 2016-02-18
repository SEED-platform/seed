import logging
import time
from datetime import date, timedelta, datetime

# from billiard import current_process # was used in green_button_task_runner
# from celery import current_app # was used in green_button_task_runner
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from seed.energy.meter_data_processor.monthly_data_aggregator import aggr_sum_metric

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
def green_button_task_runner():
    # Get total number of processes and current process index, to set offset
    # Tasks are distributed to all workers in Round-Robin style
    # NL: This is supposedly deprecated. Commenting out for now
    _log.debug("running green_button_task_runner")
    # stats = current_app.control.inspect().stats()
    # num_process = len(stats[stats.keys()[0]]['pool']['processes'])
    # offset = current_process().index
    #
    # record = ts_parser_record.objects.filter(active='Y')
    # if record:
    #     today_date = date.today()
    #     today_str = today_date.strftime('%m/%d/%Y')
    #
    #     yesterday = date.today() - timedelta(1)
    #     yesterday_str = yesterday.strftime('%m/%d/%Y')
    #
    #     row_index = 0
    #     for gb_info in record:
    #         row_index = row_index + 1
    #         if row_index - 1 < offset:
    #             continue
    #         else:
    #             offset = offset + num_process
    #
    #         last_date_str = gb_info.last_date
    #         row_id = gb_info.id
    #         url = gb_info.url
    #         subscription_id = gb_info.subscription_id
    #         last_ts = gb_info.last_ts
    #         min_date_parameter = gb_info.min_date_parameter
    #         max_date_parameter = gb_info.max_date_parameter
    #         building_id = gb_info.building_id
    #
    #         time_type = gb_info.time_type
    #         if time_type == 'date':
    #             date_pattern = gb_info.date_pattern
    #
    #             last_datetime = datetime.strptime(last_date_str, date_pattern)
    #             last_date = last_datetime.date()
    #
    #             if last_date > yesterday:
    #                 _log.info('Green Button last date is beyond yesterday')
    #                 continue
    #
    #             url = url + settings.GREEN_BUTTON_BATCH_URL_SYNTAX + subscription_id + "&" + min_date_parameter + "=" + last_date_str + "&" + max_date_parameter + "=" + yesterday_str
    #         elif time_type == 'timestamp':
    #             last_date = long(last_date_str)
    #             if last_date > yesterday:
    #                 _log.info('Green Button last date is beyond yesterday')
    #                 continue
    #             yesterday_timestamp = str(calendar.timegm(time.strptime(yesterday_str, '%m/%d/%Y')))
    #             url = url + settings.GREEN_BUTTON_BATCH_URL_SYNTAX + subscription_id + "&" + min_date_parameter + "=" + last_date_str + "&" + max_date_parameter + "=" + str(
    #                 yesterday)
    #
    #         _log.info('Fetching url ' + url)
    #
    #         ts_data = driver.get_gb_data(url, building_id)
    #
    #         _log.info('data fetched')
    #
    #         if ts_data is not None:
    #             analyser.data_analyse(ts_data, 'GreenButton')
    #
    #         _log.info('update db record: last_date=\'' + today_str + '\' for id=' + str(row_id))
    #         record = GreenButtonBatchRequestsInfo.objects.get(id=row_id)
    #         record.last_date = today_str
    #         record.save()
    # else:
    #     _log.info('No GreenButton record info found')


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

    # first day of last month
    # firstDayOfLastMonth = lastmonth.replace(day=1).replace(hour=0).replace(minute=0).replace(second=0).replace(
    #    microsecond=0)  # Not used

    # last day of the month
    if lastmonth.month in monthlist:
        lastDayOfLastMonth = lastmonth.replace(day=31)
    elif (lastmonth.month == 2) and (lastmonth.year % 4 != 0):
        lastDayOfLastMonth = lastmonth.replace(day=28)
    elif (lastmonth.month == 2) and (lastmonth.year % 4 == 0):
        lastDayOfLastMonth = lastmonth.replace(day=29)
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
