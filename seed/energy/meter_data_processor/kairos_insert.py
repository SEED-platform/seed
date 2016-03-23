import json
import logging

import requests
import time
import random
from time import sleep

from django.conf import settings

_log = logging.getLogger(__name__)
KairosDB_Batch_Insert_Size = 1000


def is_insert_finish(start_ts, end_ts, insert_checker, count):
    tsdb_info = settings.TSDB

    query_body = {}
    query_body['start_absolute'] = start_ts
    query_body['end_absolute'] = end_ts

    query_body['metrics'] = []

    metric = {}
    metric['tags'] = {}
    metric['tags']['insert_checker'] = insert_checker
    metric['name'] = str(tsdb_info['measurement'])

    aggregator = {}
    aggregator['name'] = 'count'
    aggregator_sampling = {}
    aggregator_sampling['value'] = 1
    aggregator_sampling['unit'] = 'minutes'
    aggregator['sampling'] = aggregator_sampling
    aggregators = []
    aggregators.append(aggregator)
    metric['aggregators'] = aggregators

    group_by = {}
    group_by['name'] = 'tag'
    group_by['tags'] = ['insert_checker']
    group_bys = []
    group_bys.append(group_by)
    metric['group_by'] = group_bys

    query_body['metrics'].append(metric)

    data = json.dumps(query_body)

    headers = {'content-type': 'application/json'}
    resp = requests.post(tsdb_info['query_url'], data=data, headers=headers)

    q_count = resp.json()['queries'][0]['sample_size']

    if int(q_count) >= count:
        return True

    return False


def batch_insert_kairosdb(meta_data, ts_data):
    wrap = []
    db_data = settings.TSDB

    total_len = len(meta_data)
    counter = 0
    for ts, meta in zip(ts_data, meta_data):
        insert_data = {}
        insert_data['name'] = db_data['measurement']
        insert_data['timestamp'] = str(ts[0]) + '000'
        insert_data['type'] = 'double'
        insert_data['value'] = ts[2]
        insert_data['tags'] = meta

        wrap.append(insert_data)
        if len(wrap) == KairosDB_Batch_Insert_Size:
            json_insert_data = json.dumps(wrap)
            r = requests.post(db_data['insert_url'], data=json_insert_data)
            if r.status_code != 204:
                _log.error('Insert Into KairosDB Error ' + str(r.status_code))
                _log.info('Error Message: ' + r.text)
                return False

            counter += KairosDB_Batch_Insert_Size
            _log.info('KairosDB_Inserted, ' + str(counter) + '/' + str(total_len))
            wrap = []

    if len(wrap) > 0:
        json_insert_data = json.dumps(wrap)
        r = requests.post(db_data['insert_url'], data=json_insert_data)
        if r.status_code != 204:
            _log.error('Insert Into KairosDB Error ' + str(r.status_code))
            _log.info('Error Message: ' + r.text)
            return False

    return True


# timestamp is in millisecond unit
def update_timestamp_record(timestamps, is_last_timestamp):
    headers = {'content-type': 'application/json'}

    tsdb_info = settings.TSDB
    tsdb_url = tsdb_info['query_url']

    meta_timestamp = 1 if is_last_timestamp else 2
    meta_type = 'energy_last_timestamp' if is_last_timestamp else 'energy_first_timestamp'

    # query existing last timestamp
    bld_ids = list(timestamps.keys())

    query_body = {}
    query_body['start_absolute'] = meta_timestamp
    query_body['end_absolute'] = meta_timestamp
    query_body['metrics'] = []

    metric = {}
    metric['tags'] = {}
    metric['tags']['canonical_id'] = bld_ids
    metric['tags']['meta_type'] = meta_type
    metric['name'] = str(tsdb_info['measurement'])

    aggregator = {}
    aggregator['name'] = 'avg'
    aggregator['align_sampling'] = True
    aggregator_sampling = {}
    aggregator_sampling['value'] = 1
    aggregator_sampling['unit'] = 'minutes'
    aggregator['sampling'] = aggregator_sampling
    aggregators = []
    aggregators.append(aggregator)
    metric['aggregators'] = aggregators

    group_by = {}
    group_by['name'] = 'tag'
    group_by['tags'] = ['canonical_id']
    group_bys = []
    group_bys.append(group_by)
    metric['group_by'] = group_bys

    query_body['metrics'].append(metric)

    data = json.dumps(query_body)

    r = requests.post(tsdb_url, data=data, headers=headers)

    if r.status_code != 200:
        _log.error('query building existing timestamp error')
        _log.error(r.status_code)
        _log.error(r.text)
        print r.status_code
        print r.text
        return False
    else:
        res = r.json()['queries'][0]['results']

        # compare timestamp from uploaded data with previous record if there is any
        for entry in res:
            tags = entry['tags']
            if not tags:
                continue

            bld_id = tags['canonical_id'][0]
            ts = int(entry['values'][0][0])

            if (is_last_timestamp and ts >= timestamps[bld_id]) or (not is_last_timestamp and ts <= timestamps[bld_id]):
                # existing timestamp is later than uploaded last timestamp, or earlier than uploaded first timestamp
                # delete this entry in dictionary
                timestamps.pop(bld_id, None)

    insert_wrap = []

    # insert new/updated timestamp into KairosDB
    for bld_id, ts in timestamps.iteritems():
        insert_data = {}
        insert_data['name'] = tsdb_info['measurement']
        insert_data['timestamp'] = meta_timestamp

        insert_data['value'] = str(ts)

        tags = {}
        tags['canonical_id'] = bld_id
        tags['meta_type'] = meta_type
        insert_data['tags'] = tags

        insert_wrap.append(insert_data)

    json_insert_data = json.dumps(insert_wrap)

    r = requests.post(tsdb_info['insert_url'], data=json_insert_data)

    if r.status_code != 204:
        _log.error('Insert Into KairosDB Error ' + str(r.status_code))
        _log.info('Error Message: ' + r.text)
        print r.status_code
        print r.text
        return False

    return True


# timestamp is in second unit
def insert(gb_data):
    if not gb_data:
        return True

    ret_flag = True

    # create unique tag, used to check if insert is completed
    checker = str(int(round(time.time() * 1000)))
    checker = checker + '-' + str(random.randint(0, 1000000))

    # assemble insert data
    meta_list = []
    ts_list = []

    last_timestamp = {}
    first_timestamp = {}

    for ts_cell in gb_data:
        ts_data = [ts_cell['start'], ts_cell['interval'], ts_cell['value']]
        ts_list.append(ts_data)

        bld_id = ts_cell['canonical_id']

        # get start timestamp in milliseconds
        finer_ts_start = int(ts_cell['start']) * 1000
        if (bld_id not in last_timestamp) or (finer_ts_start > last_timestamp[bld_id]):
            last_timestamp[bld_id] = finer_ts_start

        if (bld_id not in first_timestamp) or (finer_ts_start < first_timestamp[bld_id]):
            first_timestamp[bld_id] = finer_ts_start

        del ts_cell['start']
        del ts_cell['value']
        ts_cell['insert_checker'] = checker
        meta_list.append(ts_cell)

    min_ts = min(list(first_timestamp.values()))
    max_ts = max(list(last_timestamp.values()))

    # insert
    ret_flag = batch_insert_kairosdb(meta_list, ts_list)
    if ret_flag:
        update_timestamp_record(last_timestamp, True)
        update_timestamp_record(first_timestamp, False)

        print first_timestamp
        print last_timestamp

        total_num = len(gb_data)

        max_retry = 2
        while ret_flag and (not is_insert_finish(min_ts, max_ts, checker, total_num)):
            # Some time only partial data is inserted into KairosDB, redo the insert
            ret_flag = batch_insert_kairosdb(meta_list, ts_list)
            max_retry = max_retry - 1
            if max_retry == 0:
                break

            sleep(5)

    if not ret_flag:
        _log.error('KairosDB insert failed, insert_checker is ' + checker)

    return ret_flag
