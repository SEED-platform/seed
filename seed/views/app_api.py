import json
import requests
import logging

from threading import Thread
from Queue import Queue, Empty as QueueEmptyException
from datetime import datetime

from django.db.models import Min
from seed.decorators import ajax_request
from seed.utils.api import api_endpoint
from seed.energy.tsdb.kairosdb import kairosdb_detector

from django.conf import settings
from seed.models import(
    BuildingSnapshot,
    CanonicalBuilding,
    TimeSeries,
    Meter,
)

_log = logging.getLogger(__name__)


def query_canonical_snapshots(city, state, canonical_ids=None):
    if canonical_ids:
        bld_snapshot_ids = CanonicalBuilding.objects.filter(active=True).filter(pk__in=canonical_ids).values('canonical_snapshot_id')
    else:
        bld_snapshot_ids = CanonicalBuilding.objects.filter(active=True).values('canonical_snapshot_id')

    canonical_snapshots = BuildingSnapshot.objects.all().filter(id__in=bld_snapshot_ids)

    if city and state:
        canonical_snapshots = canonical_snapshots.filter(city=city).filter(state_province=state)

    return canonical_snapshots


def filter_building_snapshots(city, state, fields, canonical_ids=None, exclude_null=True):
    snapshots = query_canonical_snapshots(city, state, canonical_ids)

    if fields:
        fields = fields.split(',')
        snapshots = snapshots.values(*fields)

        if exclude_null:
            for field in fields:
                kwargs = {}
                kwargs[field + '__isnull'] = True
                snapshots = snapshots.exclude(**kwargs)
    else:
        snapshots = snapshots.values()

    return snapshots


@api_endpoint
@ajax_request
def query_building_info(request):
    '''
    Optional parameters are city, state and fields, fields is
    a comma delimited string having the queried column names

    Note: only records have not Null value on all quereid columns
    will be returned
    '''
    res = {}

    city = request.GET.get('city')
    state = request.GET.get('state')
    fields = request.GET.get('fields')

    query_result = filter_building_snapshots(city, state, fields)

    res['status'] = 'success'
    res['data'] = [r for r in query_result]
    return res


def get_meter_ids_within_range(start_datetime, end_datetime):
    ts = TimeSeries.objects.all().filter(end_time__gte=start_datetime).filter(begin_time__lte=end_datetime).values('meter_id')
    return [r['meter_id'] for r in ts]


def get_canonical_ids_from_meter_ids(meter_ids):
    canonical = Meter.objects.all().filter(id__in=meter_ids).select_related('canonical_building').order_by().distinct('canonical_building').values('canonical_building')
    return [r['canonical_building'] for r in canonical]


@api_endpoint
@ajax_request
def query_building_info_with_monthly_data(request):
    '''
    Required parameters are start_year, start_month, end_year,
    end_month and end_day

    Optional parameters are city, state and fields, fields is
    a comma delimited string having the queried column names.
    Parameter fields is same as in query_building_info API.

    Records have monthly energy data within the specified time
    period will be returned
    '''
    res = {}

    city = request.GET.get('city')
    state = request.GET.get('state')
    fields = request.GET.get('fields')

    start_year = request.GET.get('start_year')
    start_month = request.GET.get('start_month')
    end_year = request.GET.get('end_year')
    end_month = request.GET.get('end_month')
    end_day = request.GET.get('end_day')

    res = {}

    if not start_year or not start_month or not end_year or not end_month or not end_day:
        res['status'] = 'error'
        res['msg'] = 'Expecting parameters of building_type, start_year, end_year, start_month, end_month, and end_day'
        return res

    try:
        start_time = datetime(int(start_year), int(start_month), 1, 0, 0, 0)
        end_time = datetime(int(end_year), int(end_month), int(end_day), 23, 59, 59)
    except:
        res['status'] = 'error'
        res['msg'] = 'start_year and start_month or end_year and end_month are not valid year month numbers'
        return res

    meter_ids = get_meter_ids_within_range(start_time, end_time)
    canonical_ids = get_canonical_ids_from_meter_ids(meter_ids)

    query_result = filter_building_snapshots(city, state, fields, canonical_ids=canonical_ids)

    res['status'] = 'success'
    res['data'] = [r for r in query_result]
    return res


@api_endpoint
@ajax_request
def query_canonical_meter_pairs(request):
    '''
    Optional parameters are city, state and fields, fields is
    a comma delimited string having the queried column names.
    Parameter fields is same as in query_building_info API.

    Return list of {canonical_id, meter_id} pairs
    '''
    res = {}

    city = request.GET.get('city')
    state = request.GET.get('state')
    fields = 'canonical_building_id'

    query_result = filter_building_snapshots(city, state, fields)
    canonical_ids = [r['canonical_building_id'] for r in query_result]

    canonical_meter_pairs = get_building_canonical_id_meter_pairs(canonical_ids)

    res['status'] = 'success'
    res['data'] = canonical_meter_pairs
    return res


@api_endpoint
@ajax_request
def query_canonical_meter_pairs_and_info(request):
    '''
    Optional parameters are city, state and fields, fields is
    a comma delimited string having the queried column names.
    Parameter fields is same as in query_building_info API.

    Return a list of {canonical_id, meter_id} pairs and the info
    of meters appear in the list
    '''
    res = {}

    city = request.GET.get('city')
    state = request.GET.get('state')
    fields = 'canonical_building_id'

    query_result = filter_building_snapshots(city, state, fields)
    canonical_ids = [r['canonical_building_id'] for r in query_result]

    canonical_meter_pairs = get_building_canonical_id_meter_pairs(canonical_ids)
    meter_ids = [r['meters'] for r in canonical_meter_pairs]
    meter_info = get_meter_info(meter_ids)

    data = {}
    data['canonical_meter_pairs'] = canonical_meter_pairs
    data['meter_info'] = meter_info

    res['status'] = 'success'
    res['data'] = data
    return res


def get_buildings_finer_timeseries_start_end(canonical_id=None):
    '''
    Return the very first and last timestamp of finer timeseries
    data in KairosDB

    If canonical_id is not provided, all the building's very first
    and last timestamp will be returned
    '''
    query_body = {}
    query_body['start_absolute'] = 1  # special timestamp for meta data
    query_body['end_absolute'] = 2
    query_body['metrics'] = []

    metric = {}
    metric['name'] = str(settings.TSDB['measurement'])

    if not canonical_id:
        tags = {}
        tags['canonical_id'] = canonical_id
        metric['tags'] = tags

    group_by = {}
    group_by['name'] = 'tag'
    group_by['tags'] = []
    group_by['tags'].append('meta_type')
    group_by['tags'].append('canonical_id')
    metric['group_by'] = []
    metric['group_by'].append(group_by)

    aggregator = {}
    aggregator['name'] = 'avg'
    aggregator_sampling = {}
    aggregator_sampling['value'] = 1
    aggregator_sampling['unit'] = 'minutes'
    aggregator['sampling'] = aggregator_sampling
    aggregators = []
    aggregators.append(aggregator)
    metric['aggregators'] = aggregators

    query_body['metrics'].append(metric)

    query_str = json.dumps(query_body)

    headers = {'content-type': 'application/json'}

    response = requests.post(settings.TSDB['query_url'], data=query_str, headers=headers)

    ret = {}
    json_data = response.json()
    if response.status_code == 200:
        ret['status'] = 'success'

        data = {}
        json_data = json_data['queries'][0]['results']
        for data_entry in json_data:
            bld_canonical_id = data_entry['tags']['canonical_id'][0]
            meta_type = data_entry['tags']['meta_type'][0]
            timestamp = data_entry['values'][0][1]

            if bld_canonical_id not in data:
                data[bld_canonical_id] = {}

            data[bld_canonical_id][meta_type] = timestamp
        ret['data'] = data
    else:
        ret['status'] = 'error'
        ret['error_code'] = response.status_code
        ret['msg'] = json_data['errors'][0]

    return ret


def do_days_query(q):
    '''
    Fetch a task fro Queue, and query KairosDB.

    The task provides building id, start and end time,
    2D array to put result, and optional energy type.

    Note: the time interval between start and end time
    is 10 days for optimal query performance

    The daily energy data will be put into the 2D array,
    first dimension is days, second dimention is 24 hours
    '''
    while True:
        try:
            arg = q.get(False)
        except QueueEmptyException:
            # print "Queue is empty"
            return

        energy_type = arg['energy_type']

        query_body = {}
        query_body['start_absolute'] = arg['start']
        query_body['end_absolute'] = arg['end']
        query_body['metrics'] = []

        metric = {}
        metric['name'] = str(settings.TSDB['measurement'])

        tags = {}
        tags['canonical_id'] = []
        tags['canonical_id'].append(arg['canonical_id'])

        if not energy_type:
            tags['energy_type'] = []
            tags['energy_type'].append(energy_type)

        metric['tags'] = tags

        group_by = {}
        group_by['name'] = 'tag'
        group_by['tags'] = []
        group_by['tags'].append('canonical_id')
        metric['group_by'] = []
        metric['group_by'].append(group_by)

        aggregator = {}
        aggregator['name'] = 'sum'
        aggregator_sampling = {}
        aggregator_sampling['value'] = 1
        aggregator_sampling['unit'] = 'hours'
        aggregator['sampling'] = aggregator_sampling
        aggregators = []
        aggregators.append(aggregator)
        metric['aggregators'] = aggregators

        query_body['metrics'].append(metric)

        query_str = json.dumps(query_body)

        headers = {'content-type': 'application/json'}

        response = requests.post(settings.TSDB['query_url'], data=query_str, headers=headers)

        if response.status_code == 200:
            json_data = response.json()
            values = json_data['queries'][0]['results'][0]['values']
            del values[240:]

            result = arg['result']
            values = [value[1] for value in values]

            day = arg['start_day']
            for d in xrange(arg['days']):
                result[day + d] = values[d * 24: (d + 1) * 24]
        else:
            _log.error(response.status_code)
            _log.error(response.text)

        q.task_done()


def get_daily_ts_data(canonical_id, query_start, query_end, days, energy_type):
    '''
    Query KairosDB for daily energy data of a building.

    Note: the time interval days should be a multiplier of ten.
    The start time is query_end - days, the end time is query_end.

    Divide the query into batch of 10 day query and put the
    pending queries into a queue with necessary data. Then
    a group of threads will be launched to fetch the pending
    query from the queue to do parallel KairosDB query.
    '''

    res = [[0 for x in range(24)] for x in range(days)]

    q = Queue(days / 10)

    daily_milliseconds = 24 * 3600 * 1000
    delta_milliseconds = days * daily_milliseconds
    timestamp = query_end - delta_milliseconds
    if timestamp < query_start:
        timestamp = query_start

    day = 0
    while timestamp < query_end and day < days:
        arg = {}
        arg['start'] = timestamp
        arg['end'] = timestamp + daily_milliseconds * 10 - 1
        arg['start_day'] = day
        arg['days'] = 10
        arg['canonical_id'] = canonical_id
        arg['result'] = res
        arg['track'] = day
        arg['total'] = days
        arg['energy_type'] = energy_type
        q.put(arg)

        timestamp += daily_milliseconds * 10
        day += 10

    thread_args = []
    thread_args.append(q)
    threads = [Thread(target=do_days_query, args=thread_args) for i in xrange(days / 10)]
    for t in threads:
        t.start()

    q.join()

    return res


@api_endpoint
@ajax_request
def query_building_finer_ts_from_latest(request):
    '''
    Query building's daily energy consumption of the last
    given number of days. E.g., if a building has finer
    timeseries data till 2015-12-31, the last 10 days data
    is from 2015-12-21

    Required parameters are days_till_last and canonical_id.

    Optional parameter is energy_type
    '''
    res = {}

    if not kairosdb_detector.detect():
        res['status'] = 'error'
        res['msg'] = 'No timeseries database found'
        return res

    days_till_last = request.GET.get('days_till_last')
    canonical_id = request.GET.get('canonical_id')

    if not days_till_last or not canonical_id:
        res['status'] = 'error'
        res['msg'] = 'Expecting integer parameter days_till_last and canonical_id, days_till_last is tens'
        return res

    try:
        days_till_last = int(days_till_last)
        canonical_id = str(int(canonical_id))
    except ValueError:
        res['status'] = 'error'
        res['msg'] = 'Expecting integer parameter days_till_last and canonical_id, days_till_last is tens'
        return res

    if days_till_last % 10 != 0:
        res['status'] = 'error'
        res['msg'] = 'Expecting tnes integer parameter days_till_last'
        return res

    energy_type = request.GET.get('energy_type')

    building_ts_data_start_end = get_buildings_finer_timeseries_start_end(canonical_id=canonical_id)
    if building_ts_data_start_end['status'] != 'success':
        res['status'] = 'error'
        res['msg'] = 'Query KairosDB error when try to get building timeseries data start and end time, canonical id is ' + str(canonical_id)
        res['error_msg'] = building_ts_data_start_end['msg']
        res['error_code'] = building_ts_data_start_end['error_code']
        return res

    start_ends = building_ts_data_start_end['data']

    if canonical_id not in start_ends:
        res['status'] = 'error'
        res['msg'] = 'Start and end timestamp not found in KairosDB, canonial id is ' + str(canonical_id)
        return res

    start_end = start_ends[canonical_id]
    query_start = start_end['energy_first_timestamp']
    query_end = start_end['energy_last_timestamp']

    daily_data = get_daily_ts_data(canonical_id, query_start, query_end, days_till_last, energy_type)

    res['status'] = 'success'
    res['data'] = daily_data

    return res


@api_endpoint
@ajax_request
def earliest_timeseries_data_year(request):
    '''
    Return the year of earliest finer timeseries data

    Optional parameters are city and state
    '''
    city = request.GET.get('city')
    state = request.GET.get('state')

    if city and state:
        blds_ids = BuildingSnapshot.objects.all().exclude(use_description__isnull=True).exclude(use_description__exact='').exclude(postal_code__isnull=True).exclude(postal_code__exact='').filter(city=city).filter(state_province=state).order_by().distinct('canonical_building_id').values('canonical_building_id')
    else:
        blds_ids = BuildingSnapshot.objects.all().exclude(use_description__isnull=True).exclude(use_description__exact='').exclude(postal_code__isnull=True).exclude(postal_code__exact='').order_by().distinct('canonical_building_id').values('canonical_building_id')

    blds_ids = [record['canonical_building_id'] for record in blds_ids]

    meter_ids = CanonicalBuilding.objects.all().filter(pk__in=blds_ids).select_related('meters').filter(meters__isnull=False).values('meters')
    meter_ids = [record['meters'] for record in meter_ids]

    ts_ids = Meter.objects.all().filter(id__in=meter_ids).select_related('timeseries_data').values('timeseries_data')
    ts_ids = [record['timeseries_data'] for record in ts_ids]

    earliest_time = TimeSeries.objects.all().filter(id__in=ts_ids).aggregate(Min('begin_time'))
    earliest_year = earliest_time['begin_time__min'].year

    res = {}
    res['status'] = 'success'
    res['data'] = earliest_year
    return res


def get_building_monthly_energy_consumption_from_meters(meter_ids, start_time, end_time):
    '''
    Since the montly energy consumption's start and end timestamp
    may not necessarily lay on very first and end day of month, any
    record has overlap with give time period will be returned.

    Note: no data interpolation applied, just raw data
    '''
    if not meter_ids:
        return None

    if len(meter_ids) == 1:
        query_res = TimeSeries.objects.all().filter(meter_id=meter_ids[0]).filter(end_time__gte=start_time).filter(begin_time__lte=end_time).values()
    else:
        query_res = TimeSeries.objects.all().filter(meter_id__in=meter_ids).filter(end_time__gte=start_time).filter(begin_time__lte=end_time).values()

    return [r for r in query_res]


def get_building_canonical_id_meter_pairs(canonical_ids):
    if not canonical_ids:
        return None

    if len(canonical_ids) == 1:
        query_res = CanonicalBuilding.objects.all().filter(pk=canonical_ids[0]).select_related('meters').filter(meters__isnull=False).values('pk', 'meters')
    else:
        query_res = CanonicalBuilding.objects.all().filter(pk__in=canonical_ids).select_related('meters').filter(meters__isnull=False).values('pk', 'meters')

    return [r for r in query_res]


def get_meter_info(meter_ids):
    if not meter_ids:
        return None

    if len(meter_ids) == 1:
        query_res = Meter.objects.all().filter(id=meter_ids[0])
    else:
        query_res = Meter.objects.all().filter(id__in=meter_ids)

    return [r for r in query_res.values()]


def get_building_monthly_energy_consumption_from_canonical_ids(canonical_ids, start_time, end_time):
    canonical_meter_pairs = get_building_canonical_id_meter_pairs(canonical_ids)
    meter_ids = [r['meters'] for r in canonical_meter_pairs]

    energy_consumption = get_building_monthly_energy_consumption_from_meters(meter_ids, start_time, end_time)
    return energy_consumption


@api_endpoint
@ajax_request
def get_building_monthly_energy_consumptions_by_building_type(request):
    '''
    Return monthly energy consumption records with given time interval of
    buildings that belong to the given building type.

    Required parameters are building_type, start_year, start_month, end_year,
    end_month, and end_day

    Optional parameters are city and state

    Note: the building type is read from column of use_description
    '''

    building_type = request.GET.get('building_type')
    start_year = request.GET.get('start_year')
    start_month = request.GET.get('start_month')
    end_year = request.GET.get('end_year')
    end_month = request.GET.get('end_month')
    end_day = request.GET.get('end_day')

    res = {}

    if not building_type or not start_year or not start_month or not end_year or not end_month or not end_day:
        res['status'] = 'error'
        res['msg'] = 'Expecting parameters of building_type, start_year, end_year, start_month, end_month, and end_day'
        return res

    try:
        start_time = datetime(int(start_year), int(start_month), 1, 0, 0, 0)
        end_time = datetime(int(end_year), int(end_month), int(end_day), 23, 59, 59)
    except:
        res['status'] = 'error'
        res['msg'] = 'start_year and start_month or end_year and end_month are not valid year month numbers'
        return res

    city = request.GET.get('city')
    state = request.GET.get('state')

    canonical_snapshots = query_canonical_snapshots(city, state)
    if building_type == 'all_building':
        canonical_snapshots = canonical_snapshots.exclude(use_description__isnull=True).exclude(use_description__exact='')
    else:
        canonical_snapshots = canonical_snapshots.filter(use_description=building_type)

    canonical_ids = [r['canonical_building_id'] for r in canonical_snapshots.values()]

    energy_consumption = get_building_monthly_energy_consumption_from_canonical_ids(canonical_ids, start_time, end_time)

    res['status'] = 'success'
    res['data'] = energy_consumption
    return res


@api_endpoint
@ajax_request
def get_building_monthly_energy_consumptions_by_meter(request):
    '''
    Return the monthly energy consumption of the given meter(s)

    Required parameters are start_year, start_month, end_year,
    end_month and end_day
    '''

    meter_ids = request.GET.get('meter_ids')
    start_year = request.GET.get('start_year')
    start_month = request.GET.get('start_month')
    end_year = request.GET.get('end_year')
    end_month = request.GET.get('end_month')
    end_day = request.GET.get('end_day')

    res = {}

    try:
        start_time = datetime(int(start_year), int(start_month), 1, 0, 0, 0)
        end_time = datetime(int(end_year), int(end_month), int(end_day), 23, 59, 59)
    except:
        res['status'] = 'error'
        res['msg'] = 'start_year and start_month or end_year and end_month are not valid year month numbers'
        return res

    meter_ids = meter_ids.split(',')
    energy_consumption = get_building_monthly_energy_consumption_from_meters(meter_ids, start_time, end_time)

    res['status'] = 'success'
    res['data'] = energy_consumption
    return res
