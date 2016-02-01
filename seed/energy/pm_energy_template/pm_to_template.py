# read a folder containing excel files downloaded from EnergyStar PM
import os
import pandas as pd
import glob

import logging
_log = logging.getLogger(__name__)

def read_pm(file_path):
    upload_dir = 'static/uploads/'
    filelist = glob.glob(file_path)
    for excel in filelist:
        process_one_file(excel, file_path)

def process_one_file(filename, file_path):
    _log.info('convert file{0} to template'.format(filename))

    df_address = pd.read_excel(filename, sheetname=0, skiprows=2, header=2, parse_cols = [1, 2])
    address_dict = dict(zip(df_address['Portfolio Manager ID'],
                           df_address['Street Address']))
    df_energy = pd.read_excel(filename, sheetname=5, skiprows=3, header=2, parse_cols = [0, 1, 2, 4, 6, 7, 9, 10, 11])
    df_energy.insert(0, 'Street Address',
                     df_energy['Portfolio Manager ID'].map(lambda x:
                                                           address_dict[x]))
    df_energy.info()
    df_energy.rename(columns={'Portfolio Manager ID': 'Custom ID',
                              'Portfolio Manager Meter ID':'Custom Meter ID'},
                     inplace=True)

    file_out = file_path[len(file_path):-5] + '_processed.xlsx'
    df_energy.to_excel(file_out, index=False)

