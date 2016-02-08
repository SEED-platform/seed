from django.db.models import Q
from seed.models import (
    GreenButtonBatchRequestsInfo,
)
from billiard import current_process
from django.conf import settings 

from celery import shared_task

#import psycopg2
import time
import calendar
import sys
import logging
from datetime import date, timedelta, datetime

from seed.energy.meter_data_processor import green_button_driver as driver
from seed.energy.meter_data_processor import green_button_data_analyser as analyser
from seed.energy.meter_data_processor import kairos_insert as db_insert

_log = logging.getLogger(__name__)

def increment_day(date_str):
    '''
    Format of date_str is MM/DD/YYYY
    '''

    if date_str == '' or date_str == None:
        newdate = date.today()-timedelta(1)
    else: 
        t=time.strptime(date_str, '%m/%d/%Y')
        newdate=date(t.tm_year,t.tm_mon,t.tm_mday)+timedelta(1)
    
    return newdate.strftime('%m/%d/%Y')


@shared_task(name='green_button_task_runner')
def green_button_task_runner():
    # Get total number of processes and current process index, to set offset
    # Tasks are distributed to all workers in Round-Robin style
    stats = current_app.control.inspect().stats()
    num_process = len(stats[stats.keys()[0]]['pool']['processes'])
    offset = current_process().index

    record = ts_parser_record.objects.filter(active='Y')
    if record:
        today_date = date.today()
        today_str = today_date.strftime('%m/%d/%Y')

        yesterday = date.today() - timedelta(1)
        yesterday_str = yesterday.strftime('%m/%d/%Y')

        row_index = 0
        for gb_info in record:
            row_index = row_index+1
            if row_index-1 < offset:
                continue
            else:
                offset = offset + num_process
            
            last_date_str = gb_info.last_date
            row_id = gb_info.id
            url = gb_info.url
            subscription_id = gb_info.subscription_id
            last_ts = gb_info.last_ts
            min_date_parameter = gb_info.min_date_parameter
            max_date_parameter = gb_info.max_date_parameter
            building_id = gb_info.building_id
        
            time_type = gb_info.time_type
            if time_type == 'date':
                date_pattern = gb_info.date_pattern
            
                last_datetime = datetime.strptime(last_date_str, date_pattern)
                last_date = last_datetime.date()

                if last_date > yesterday:
                    _log.info('Green Button last date is beyond yesterday')
                    continue 
            
                url = url+settings.GREEN_BUTTON_BATCH_URL_SYNTAX+subscription_id+"&"+min_date_parameter+"="+last_date_str+"&"+max_date_parameter+"="+yesterday_str
            elif time_type == 'timestamp':
                last_date = long(last_date_str)
                if last_date > yesterday:
                    _log.info('Green Button last date is beyond yesterday')
                    continue
                yesterday_timestamp = str(calendar.timegm(time.strptime(yesterday_str, '%m/%d/%Y')))
                url = url+settings.GREEN_BUTTON_BATCH_URL_SYNTAX+subscription_id+"&"+min_date_parameter+"="+last_date_str+"&"+max_date_parameter+"="+str(yesterday)

            _log.info('Fetching url '+url)

            ts_data = driver.get_gb_data(url, building_id)
       
            _log.info('data fetched')
 
            if ts_data!=None:
                analyser.data_analyse(ts_data, 'GreenButton')
            
            _log.info('update db record: last_date=\''+today_str+'\' for id='+str(row_id))
            record = GreenButtonBatchRequestsInfo.objects.get(id=row_id)
            record.last_date = today_str
            record.save()
    else:
        _log.info('No GreenButton record info found')
