import datetime as dt
import glob
import logging

import numpy as np
import pandas as pd

from seed.energy.pm_energy_template import query as qr

_log = logging.getLogger(__name__)


def pm_to_json(pm_file_path):
    filelist = glob.glob(pm_file_path)
    for excel in filelist:
        pm_to_json_single(excel, pm_file_path)


def pm_to_json_single(excel, file_path):
    '''
    Assume PM is in local time
    '''

    meter_con_df = pd.read_excel(excel, sheetname=0)
    
    # Replace empty cell with NaN
    for c in meter_con_df.select_dtypes(include=["object"]).columns:
        meter_con_df[c] = meter_con_df[c].replace('', np.nan)

    # Remove rows missing critical data
    meter_con_df = meter_con_df.dropna(axis=0, how='any', subset = ['Street Address', 
                                                                    'Meter Type', 
                                                                    'Start Date', 
                                                                    'End Date', 
                                                                    'Usage/Quantity', 
                                                                    'Usage Units'])

    # Set default value if non-critical fields are missing
    meter_con_df['Custom Meter ID'] = meter_con_df.apply(lambda row: row['Meter Type'] + '_Meter' if np.isnan(row['Custom Meter ID']) else row['Custom Meter ID'], axis=1) # axis=1, apply to each row
    meter_con_df['Custom ID'] = meter_con_df.apply(lambda row:'1' if np.isnan(row['Custom ID']) else row['Custom ID'], axis=1)
    meter_con_df['Cost ($)'] = meter_con_df.apply(lambda row:'NA' if np.isnan(row['Cost ($)']) else row['Cost ($)'], axis=1)

    _log.info('start query')
    address = meter_con_df['Street Address'].values
    address_dict = {}
    for a in np.nditer(address, flags=['refs_ok']):
        address_dict['{0}'.format(a)] = None
    qr.retrieve_building_id(address_dict)
    _log.debug('address_dict: {0}'.format(address_dict))

    meter_con_df['buildingsnapshot_id'] = meter_con_df['Street Address'].map(lambda x: address_dict[x]['buildingsnapshot_id'])
    meter_con_df['canonical_id'] = meter_con_df['Street Address'].map(lambda x: address_dict[x]['canonical_building'])
    _log.info('end query')

    # Calculate time interval of days
    meter_con_df['interval'] = meter_con_df['End Date'] - meter_con_df['Start Date']

    meter_con_df['End Date'] = meter_con_df['End Date'].map(lambda x: x + dt.timedelta(hours=12))
    meter_con_df['Start Date'] = meter_con_df['Start Date'].map(lambda x: x + dt.timedelta(hours=12))

    meter_con_df['reading_kind'] = 'energy'

    # renaming columns of df
    name_lookup = {u'Start Date': u'start',
                   u'End Date': u'end',
                   u'Custom ID': u'custom_id',
                   u'Custom Meter ID': u'custom_meter_id',
                   u'Usage/Quantity': u'value',
                   u'Usage Units': 'uom',
                   u'Cost ($)': u'cost',
                   u'Meter Type': u'energy_type',
                   u'Street Address': u'Street_Address',
                   u'Property Name': u'Property_Name'}

    meter_con_df = meter_con_df.rename(columns=name_lookup)

    file_out = file_path[0:-5] + '_json.txt'
    # the 'interval' output is in [ns], so use ns for all time object and
    # post process with postProcess.py
    meter_con_df.to_json(file_out, 'records',
                         date_unit='ns')
