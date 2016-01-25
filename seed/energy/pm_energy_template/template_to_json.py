import os
import pandas as pd
import json
import glob
import numpy as np
import datetime as dt

from seed.energy.pm_energy_template import query as qr

import logging
_log = logging.getLogger(__name__)

def pm_to_json(pm_file_path):
    filelist = glob.glob(pm_file_path)
    for excel in filelist:
        pm_to_json_single(excel, pm_file_path)

def pm_to_json_single(excel, file_path):
    '''
    Assume PM is in local time
    '''
    _log.info('\ntemplate to json:{0}'.format(excel))
    meter_con_df = pd.read_excel(excel, sheetname=0)
    _log.debug(meter_con_df.ix[:10])

    _log.info('start query')
    address = meter_con_df['Street Address'].values
    address_dict = {}
    for a in np.nditer(address, flags=['refs_ok']):
        address_dict['{0}'.format(a)] = None
    qr.retrieve_building_id(address_dict)
    _log.debug('address_dict: {0}'.format(address_dict))

    meter_con_df['buildingsnapshot_id'] = meter_con_df['Street Address'].map(lambda x:address_dict[x]['buildingsnapshot_id'])
    meter_con_df['canonical_id'] = meter_con_df['Street Address'].map(lambda x:address_dict[x]['canonical_building'])
    _log.info('end query')

    # Calculate time interval of days
    meter_con_df['interval'] = meter_con_df['End Date'] - meter_con_df['Start Date']

    meter_con_df['End Date'] = meter_con_df['End Date'].map(lambda x: x+dt.timedelta(hours=12))
    meter_con_df['Start Date'] = meter_con_df['Start Date'].map(lambda x: x+dt.timedelta(hours=12))

    meter_con_df['reading_kind'] = 'energy'

    meter_con_df['Custom Meter ID'] = meter_con_df.apply(lambda row:row['Meter Type']+'_Meter' if np.isnan(row['Custom Meter ID']) else row['Custom Meter ID'], axis=1)

    # renaming columns of df
    name_lookup = {u'Start Date':u'start',
                   u'End Date':u'end',
                   u'Custom ID':u'custom_id',
                   u'Custom Meter ID':u'custom_meter_id',
                   u'Usage/Quantity':u'value',
                   u'Usage Units':'uom',
                   u'Cost ($)':u'cost',
                   u'Meter Type':u'energy_type',
                   u'Street Address':u'Street_Address',
                   u'Property Name':u'Property_Name'}

    meter_con_df = meter_con_df.rename(columns=name_lookup)

    file_out = file_path[len(file_path):-5] + '_json.txt'
    # the 'interval' output is in [ns], so use ns for all time object and
    # post process with postProcess.py
    meter_con_df.to_json(file_out, 'records',
                         date_unit = 'ns')
