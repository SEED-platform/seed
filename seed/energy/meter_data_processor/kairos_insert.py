import json
import logging

import requests
from django.conf import settings

_log = logging.getLogger(__name__)


def batch_insert_kairosdb(meta_data, ts_data):
    wrap = []
    db_data = settings.TSDB

    for ts, meta in zip(ts_data, meta_data):
        insert_data = {}
        insert_data['name'] = db_data['measurement']
        insert_data['timestamp'] = str(ts[0]) + '000'
        insert_data['type'] = 'double'
        insert_data['value'] = ts[2]
        insert_data['tags'] = meta

        wrap.append(insert_data)

    json_insert_data = json.dumps(wrap)

    r = requests.post(db_data['insert_url'], data=json_insert_data)

    if r.status_code != 204:
        _log.error('Insert Into KairosDB Error ' + str(r.status_code))
        _log.info('Error Message: ' + r.text)
        return False
    return True


def insert(gb_data):
    # assemble insert data
    meta_list = []
    ts_list = []

    for ts_cell in gb_data:
        ts_data = [ts_cell['start'], ts_cell['interval'], ts_cell['value']]
        ts_list.append(ts_data)

        del ts_cell['start']
        del ts_cell['value']
        meta_list.append(ts_cell)

    # insert
    return batch_insert_kairosdb(meta_list, ts_list)
