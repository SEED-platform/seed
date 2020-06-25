# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from io import BytesIO
import os
import zipfile

from seed.building_sync.building_sync import BuildingSync
from seed.building_sync.mappings import xpath_to_column_map


class BuildingSyncParser(object):
    def __init__(self, file_):
        """
        :param file_: FieldFile, an ImportFile's file
        """

        filename = file_.name
        _, file_extension = os.path.splitext(filename)

        # grab the data from the zip or xml file
        self.data = []
        if file_extension == '.zip':
            with zipfile.ZipFile(file_, 'r', zipfile.ZIP_STORED) as openzip:
                filelist = openzip.infolist()
                for f in filelist:
                    if '.xml' in f.filename and '__MACOSX' not in f.filename:
                        # try to import the file; it will raise an exception if it's bad
                        bs = BuildingSync()
                        try:
                            bs.import_file(BytesIO(openzip.read(f)))
                        except Exception as e:
                            raise Exception(f'Failed to parse file {f.filename}: {str(e)}')

                        self.data.append({'_xml': openzip.read(f).decode(), '_filename': f.filename})
        elif file_extension == '.xml':
            self.data.append({'_xml': file_.read().decode(), '_filename': filename})
        else:
            raise Exception(f'Unsupported file type for BuildingSync {file_extension}')

        self.first_five_rows = [d['_xml'] for d in self.data[:5]]

        # get the mapping for the first xml data
        bs = BuildingSync()
        bs.import_file(BytesIO(self.first_five_rows[0].encode()))
        base_mapping = bs.get_base_mapping()
        xpath_col_dict = xpath_to_column_map(base_mapping)
        self.headers = list(xpath_col_dict.keys())

    def num_columns(self):
        return 0
