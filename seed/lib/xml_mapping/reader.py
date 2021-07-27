# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
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
        # these properties will be construced while processing the files
        self.headers = []
        self._xpath_col_dict = {}

        filename = file_.name
        _, file_extension = os.path.splitext(filename)
        # grab the data from the zip or xml file
        self.data = []
        if file_extension == '.zip':
            with zipfile.ZipFile(file_, 'r', zipfile.ZIP_STORED) as openzip:
                filelist = openzip.infolist()
                for f in filelist:
                    if '.xml' in f.filename and '__MACOSX' not in f.filename:
                        self._add_property_to_data(openzip.read(f), f.filename)
        elif file_extension == '.xml':
            self._add_property_to_data(file_.read(), filename)

        else:
            raise Exception(f'Unsupported file type for BuildingSync {file_extension}')

        self.first_five_rows = [self._capture_row(row) for row in self.data[:5]]

    def _add_property_to_data(self, bsync_file, file_name):
        try:
            bs = BuildingSync()
            bs.import_file(BytesIO(bsync_file))
        except Exception as e:
            raise Exception(f'Error importing BuildingSync file {file_name}: {str(e)}')

        if not self._xpath_col_dict:
            # get the mapping for the first xml data
            base_mapping = bs.get_base_mapping()
            self._xpath_col_dict = xpath_to_column_map(base_mapping)
            self.headers = list(self._xpath_col_dict.keys())

        property_ = bs.process_property_xpaths(self._xpath_col_dict)
        # When importing zip files, we need to be able to determine which .xml file
        # a certain PropertyState came from (because of the linked BuildingFile model).
        # For this reason, we add this extra information here for later use in
        # the import tasks
        property_['_source_filename'] = file_name
        self.data.append(property_)

    def _capture_row(self, row):
        # If our number of "data" columns mismatches the number of "header" columns
        # it causes issues down the line. Thus we delete the '_source_filename' field
        # before adding the row (it doesn't have a corresponding 'header', ie it's
        # not used for mapping)
        row_copy = row.copy()
        del row_copy['_source_filename']

        # add the values _in order_ of our defined headers
        values = []
        for column in self.headers:
            values.append(str(row_copy[column]))

        return "|#*#|".join(values)

    def num_columns(self):
        return 0
