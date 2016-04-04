import logging
from datetime import date, datetime

import tasks
from seed.energy.tsdb.kairosdb import kairos_insert as tsdb
from seed.models import (
    Meter,
    CanonicalBuilding,
    TimeSeries,
)

_log = logging.getLogger(__name__)

global interval_threshold
interval_threshold = 60 * 60 * 24 * 20  # 20 days seconds


def get_month_from_ts(ts):
    date_obj = datetime.fromtimestamp(long(ts))
    return {'year': int(date_obj.year), 'month': int(date_obj.month)}


def data_analyse(ts_data, name):
    finer_ts = []
    monthly_ts = []

    cache = {}
    today_date = date.today()
    today_str = today_date.strftime('%m/%d/%Y')
    today_month = int(today_date.month)
    today_year = int(today_date.year)
    immediate_aggregate = False

    for ts_cell in ts_data:
        if name == 'Energy Template' or name == 'PM':
            # convert to seconds
            ts_cell['start'] = int(ts_cell['start']) / 1000
            ts_cell['interval'] = int(ts_cell['interval']) / 1000

        try:
            ts_cell['canonical_id'] = str(int(float(ts_cell['canonical_id'])))
        except ValueError:
            continue

        custom_meter_id = ts_cell['custom_meter_id']
        try:
            ts_cell['custom_meter_id'] = str(int(float(ts_cell['custom_meter_id'])))
        except ValueError:
            ts_cell['custom_meter_id'] = custom_meter_id

        interval = int(ts_cell['interval'])
        building_id = str(ts_cell['canonical_id'])
        custom_meter_id = str(ts_cell['custom_meter_id'])

        if interval < interval_threshold:
            ts_cell['insert_date'] = today_str

            ts_dateObj = get_month_from_ts(ts_cell['start'])
            if ts_dateObj['month'] != today_month or ts_dateObj['year'] != today_year:
                # has back filling
                immediate_aggregate = True

            finer_ts.append(ts_cell)
        else:
            monthly_ts.append(ts_cell)

        # create or retrieve seed_meter_id
        if not building_id + '_' + custom_meter_id in cache:
            res = Meter.objects.filter(custom_meter_id=custom_meter_id).select_related().filter(
                canonical_building=building_id
            )
            if not res:
                # create new meter record
                new_meter = Meter(name=(name + ' METER'),
                                  energy_type=ts_cell['energy_type_int'],
                                  energy_units=ts_cell['uom_int'],
                                  custom_meter_id=ts_cell['custom_meter_id'])
                new_meter.save()
                new_meter.canonical_building.add(CanonicalBuilding.objects.get(id=building_id))

                seed_meter_id = int(new_meter.id)
            else:
                seed_meter_id = int(res[0].id)

            cache[building_id + '_' + custom_meter_id] = seed_meter_id

    for ts_cell in monthly_ts:
        building_id = str(ts_cell['canonical_id'])
        custom_meter_id = str(ts_cell['custom_meter_id'])

        seed_meter_id = int(cache[building_id + '_' + custom_meter_id])

        # save record to timeseries table
        begin_ts = int(ts_cell['start'])
        interval = int(ts_cell['interval'])

        begin_time = datetime.fromtimestamp(begin_ts)
        end_time = datetime.fromtimestamp(begin_ts + interval)
        reading = float(ts_cell['value'])

        db_record = TimeSeries.objects.filter(meter_id=seed_meter_id, begin_time=begin_time)
        if not db_record:
            db_record = TimeSeries(begin_time=begin_time,
                                   end_time=end_time,
                                   reading=reading,
                                   meter_id=seed_meter_id)
        else:
            db_record = db_record[0]
            db_record.reading = reading

        db_record.save()

    _log.info('insert monthly data into postgresql finished')

    insert_flag = tsdb.insert(finer_ts)
    _log.info('insert ts data into KairosDB finished: ' + str(insert_flag))

    if insert_flag and immediate_aggregate:
        _log.info('Having back filling data, aggregate immediately')
        tasks.aggregate_monthly_data(ts_data[0]['canonical_id'])
        _log.info('Immediate aggregation finished')
