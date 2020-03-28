# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
"""
The Reader module is intended to contain only code which reads data
out of CSV files. Fuzzy matches, application to data models happens
elsewhere.

"""
import json
import mmap
import operator
import re
import xmltodict

from builtins import str
from csv import DictReader, Sniffer

from past.builtins import basestring
from seed.data_importer.utils import kbtu_thermal_conversion_factors
from unidecode import unidecode
from xlrd import xldate, XLRDError, open_workbook, empty_cell
from xlrd.xldate import XLDateAmbiguous

(
    XL_CELL_EMPTY,
    XL_CELL_TEXT,
    XL_CELL_NUMBER,
    XL_CELL_DATE,
    XL_CELL_BOOLEAN,
    XL_CELL_ERROR,
    XL_CELL_BLANK,  # for use in debugging, gathering stats, etc
) = range(7)

ROW_DELIMITER = "|#*#|"


class GreenButtonParser(object):
    """
    This class accepts GreenButton data in XML format.

    It's expected that XML contains a 'feed' tag at the root that contains 4
    ordered 'entry' tags:
        1) Should contain Kind/Energy Type
        2) Not used but typically contains property information
        3) Should contain Unit and order of 10 information
        4) Should contain readings with start epoch times and second duration
    """

    def __init__(self, xml_file):
        self._xml_file = xml_file
        self._cache_data = None

        # Codes taken from https://bedes.lbl.gov/sites/default/files/Green%20Button%20V0.7.2%20to%20BEDES%20V2.1%20Mapping%2020170927.pdf
        self.kind_codes = {
            0: 'Electric - Grid',  # listed as 'electricity'
            1: 'Natural Gas',  # listed as 'gas'
        }
        self.uom_codes = {
            31: 'J',
            42: 'cubic meters',  # listed as 'm3'
            72: 'Wh',
            119: 'cf',  # listed as 'ft3'
            132: 'Btu',  # listed as 'btu'
            169: 'therms',  # listed as 'therm'
        }
        self.power_of_ten_codes = {
            -12: 'p',      # Pico: 10^-12
            -9: 'n',      # Nano: 10^-9
            -6: 'micro',  # Micro: 10^-6
            -3: 'm',      # Milli: 10^-3
            -1: 'd',      # Deci: 10^-1
            0: '',       # N/A
            1: 'da',     # Deca: 10^1
            2: 'h',      # Hecto: 10^2
            3: 'k',      # Kilo: 10^3
            6: 'M',      # Mega: 10^6
            9: 'G',      # Giga: 10^9
            12: 'T',      # Tera: 10^12
        }

        # US factors work for CAN factors as this is only used to find valid unit types for a given energy type
        self._thermal_factors = kbtu_thermal_conversion_factors("US")

        # These are the valid unit prefixes found in thermal conversions
        self.thermal_factor_prefixes = {
            'k': 3,
            'M': 6,
            'G': 9,
            'c': 2,
        }

    @property
    def data(self):
        """
        Reads the sections of the GreenButton XML file to parse and reformat
        the data as needed by the MetersParser.

        If a valid type and unit could not be found, an empty list is returned.
        """
        if self._cache_data is None:
            xml_string = self._xml_file.read()
            raw_data = xmltodict.parse(xml_string)

            readings_entry = raw_data['feed']['entry'][3]

            href = readings_entry['link']['@href']
            source_id = re.sub(r'/v./', '', href)

            readings = readings_entry['content']['IntervalBlock']['IntervalReading']

            type, unit, multiplier = self._parse_type_and_unit(raw_data)

            if type and unit:
                self._cache_data = [
                    {
                        'start_time': int(reading['timePeriod']['start']),
                        'source_id': source_id,
                        'duration': int(reading['timePeriod']['duration']),
                        'Meter Type': type,
                        'Usage Units': unit,
                        'Usage/Quantity': float(reading['value']) * multiplier,
                    }
                    for reading
                    in readings
                ]
            else:
                self._cache_data = []

        return self._cache_data

    def _parse_type_and_unit(self, raw_data):
        """
        Parses raw XML to read the kind and uom/powerOfTenMultiplier. Using
        those, an attempt is made to validate the type and unit as a combination
        that the application accepts.

        The if the type and unit are parsable and valid, they are returned,
        otherwise, None is returned as applicable.
        """
        kind_entry = raw_data['feed']['entry'][0]
        kind = kind_entry['content']['UsagePoint']['ServiceCategory']['kind']
        type = self.kind_codes.get(int(kind), None)

        if type is None:
            return None, None, 1

        uom_entry = raw_data['feed']['entry'][2]['content']['ReadingType']
        uom = uom_entry['uom']
        raw_base_unit = self.uom_codes.get(int(uom), '')

        power_of_ten_multiplier = int(uom_entry['powerOfTenMultiplier'])

        resulting_unit, multiplier = self._parse_valid_unit_and_multiplier(
            type,
            power_of_ten_multiplier,
            raw_base_unit
        )

        return type, resulting_unit, multiplier

    def _parse_valid_unit_and_multiplier(self, type, power_of_ten_multiplier, raw_base_unit):
        """
        Parses valid/accepted unit and multiplier using the given type and raw
        base unit. The powerOfTenMultiplier is used to find the raw unit prefix
        which is used along with the raw base unit to try to accomplish this.

        The 3 scenarios accounted for are the following in order:
        - prefix and base == valid unit (or "starts with")
        - base == valid unit
        - base similar to a valid unit

        In the first scenario, no multiplier is needed since the provided readings
        are already given in a unit that's understood by the application.

        In the second scenario, the multiplier is generated directly from the
        powerOfTenMultiplier without any adjustments.

        In the last scenario, the multiplier is generated directly from the
        powerOfTenMultiplier with an adjustment made to convert the readings
        into a unit understood by the application.

        If none of these scenarios return a validated unit, None, 1 is returned.
        """
        valid_units_for_type = self._thermal_factors[type].keys()

        raw_prefix_unit = self.power_of_ten_codes.get(power_of_ten_multiplier, None)
        raw_full_unit = "{}{}".format(raw_prefix_unit, raw_base_unit)

        # Check if the raw full unit is an exact match (or left match) with a known valid unit
        exact_match_full_unit = next(
            (key for key in valid_units_for_type if key.startswith(raw_full_unit)),
            None
        )
        if exact_match_full_unit is not None:
            return exact_match_full_unit, 1

        # Check if just the base unit is an exact match with a known valid unit
        base_unit_only_match = next(
            (key for key in valid_units_for_type if raw_base_unit == key),
            None
        )
        if base_unit_only_match is not None:
            multiplier = 10**(power_of_ten_multiplier)
            return base_unit_only_match, multiplier

        # Check if just the base unit is similar to a known valid unit
        approx_match_base_unit = next(
            (key for key in valid_units_for_type if raw_base_unit in key),
            None
        )
        if approx_match_base_unit is not None:
            # this assumes the prefix is one character long
            factor_prefix = approx_match_base_unit[0]

            # an exact match is expected for factor_prefix - if not, this should error
            multiplier = 10**(power_of_ten_multiplier - self.thermal_factor_prefixes[factor_prefix])

            return approx_match_base_unit, multiplier

        return None, 1


class GeoJSONParser(object):
    def __init__(self, json_file):
        raw_data = json.load(json_file)
        features = raw_data.get("features")
        raw_column_names = features[0].get("properties").keys()

        self.headers = [self._display_name(col) for col in raw_column_names]
        self.column_translations = {col: self._display_name(col) for col in raw_column_names}
        self.first_five_rows = [self._capture_row(feature) for feature in features[:5]]

        self.data = []
        for feature in features:
            properties = feature.get('properties')

            entry = {self.column_translations.get(k, k): v for k, v in properties.items()}
            entry["bounding_box"] = self._get_bounding_box(feature)

            self.data.append(entry)

    def _display_name(self, col):
        # Returns string with capitalized words and underscores removed
        return re.sub(r'[_]', ' ', col.title())

    def _get_bounding_box(self, feature):
        raw_coordinates = feature.get('geometry').get('coordinates')[0]
        coords_strings = [f"{coords[0]} {coords[1]}" for coords in raw_coordinates]

        return f"POLYGON (({', '.join(coords_strings)}))"

    def _capture_row(self, feature):
        stringified_values = [str(value) for value in feature.get('properties').values()]
        return "|#*#|".join(stringified_values)

    def num_columns(self):
        return len(self.headers)


class ExcelParser(object):
    """MS Excel (.xls, .xlsx) file parser for MCMParser

    usage:
            f = open('data.xls', 'rb')
            reader = MCMParser(f)
            rows = reader.next()
            for row in rows:
                # something with the row dict
            ...
            reader.seek_to_beginning()
            # rows.next() will return the first row
    """

    def __init__(self, excel_file, sheet_name=None, *args, **kwargs):
        self.cache_headers = []
        self.excel_file = excel_file
        self.sheet = self._get_sheet(excel_file, sheet_name)
        self.header_row = self._get_header_row(self.sheet)
        self.excelreader = self.XLSDictReader(self.sheet, self.header_row)

    def _get_sheet(self, f, sheet_name=None, sheet_index=0):
        """returns a xlrd sheet

        :param f: an open file of type ``file``
        :param sheet_index: the excel sheet with a 0-index
        :returns: xlrd Sheet
        """
        data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        book = open_workbook(file_contents=data, on_demand=True)
        self._workbook = book  # needed to determine datemode

        if sheet_name is None:
            return book.sheet_by_index(sheet_index)
        else:
            return book.sheet_by_name(sheet_name)

    def _get_header_row(self, sheet):
        """returns the best guess for the header row

        :param sheet: xlrd sheet
        :returns: index of header row
        """
        for row in range(sheet.nrows):
            row_contains_empty_cells = False
            for col in range(sheet.ncols):
                if sheet.cell(row, col).ctype == empty_cell.ctype:
                    row_contains_empty_cells = True
                    break
            if not row_contains_empty_cells:
                return row
        # default to first row
        return 0

    def get_value(self, item, **kwargs):
        """Handle different value types for XLS.

        :param item: xlrd cell object
        :returns: items value with dates parsed properly
        """

        if item.ctype == XL_CELL_DATE:
            try:
                date = xldate.xldate_as_datetime(item.value, self._workbook.datemode)
                return date.strftime("%Y-%m-%d %H:%M:%S")
            except XLDateAmbiguous:
                raise Exception('Date fields are not in a format that SEED can interpret. '
                                'A possible solution is to save as a CSV file and reimport.')

        if item.ctype == XL_CELL_NUMBER:
            if item.value % 1 == 0:  # integers
                return int(item.value)
            else:
                return item.value

        if isinstance(item.value, basestring):
            return unidecode(item.value)

        return item.value

    def XLSDictReader(self, sheet, header_row=0):
        """returns a generator yeilding a dict per row from the XLS/XLSX file
        https://gist.github.com/mdellavo/639082

        :param sheet: xlrd Sheet
        :param header_row: the row index to start with
        :returns: Generator yeilding a row as Dict
        """

        # save off the headers into a member variable. Only do this once. If XLSDictReader is
        # called later (which it is in `seek_to_beginning` then don't reparse the headers
        if not self.cache_headers:
            for j in range(sheet.ncols):
                self.cache_headers.append(self.get_value(sheet.cell(header_row, j)).strip())

        def item(i, j):
            """returns a tuple (column header, cell value)"""
            # self.cache_headers[j],
            return (
                self.get_value(sheet.cell(header_row, j)),
                self.get_value(sheet.cell(i, j))
            )

        # return a generator, using yield here wouldn't run until the first
        # usage causing the try/except in MCMParser _get_reader to return
        # ExcelReader for csv files
        return (
            dict(item(i, j) for j in range(sheet.ncols))
            for i in range(header_row + 1, sheet.nrows)
        )

    def seek_to_beginning(self):
        """seeks to the beginning of the file

        Since ``XLSDictReader`` is in memory, a new one is created. Note: the headers will not be
        parsed again when the XLSDictReader is loaded
        """
        self.excel_file.seek(0)
        self.excelreader = self.XLSDictReader(self.sheet, self.header_row)

    def num_columns(self):
        """gets the number of columns for the file"""
        return self.sheet.ncols

    @property
    def headers(self):
        """return ordered list of clean headers"""
        return self.cache_headers


class CSVParser(object):
    """CSV (.csv) file parser for MCMParser

    usage:
            f = open('data.csv', 'rb')
            reader = MCMParser(f)
            rows = reader.next()
            for row in rows:
                # something with the row dict
            ...
            reader.seek_to_beginning()
            # rows.next() will return the first row
    """

    def __init__(self, csvfile, *args, **kwargs):
        self.csvfile = csvfile
        self.csvreader = self._get_csv_reader(csvfile, **kwargs)

        # read the next line to get the field names
        # cleaning the superscripts also assigns the headers to the csvreader.fieldnames
        self.clean_super_scripts()

    def _get_csv_reader(self, *args, **kwargs):
        """Guess CSV dialect, and return CSV reader."""
        # Skip the first line, as csv headers are more likely to have weird
        # character distributions than the actual data.
        self.csvfile.readline()

        # Read a significant chunk of the data to improve the odds of
        # determining the dialect.  MCM is often run on very wide csv files.
        dialect = Sniffer().sniff(self.csvfile.read(16384))
        self.csvfile.seek(0)

        if 'reader_type' not in kwargs:
            return DictReader(self.csvfile)

        else:
            reader_type = kwargs.get('reader_type')
            del kwargs['reader_type']
            return reader_type(self.csvfile, dialect, **kwargs)

    def clean_super_scripts(self):
        """Replaces column names with clean ones."""
        new_fields = []
        for col in self.csvreader.fieldnames:
            new_fields.append(unidecode(col))

        self.csvreader.fieldnames = new_fields

    def seek_to_beginning(self):
        """seeks to the beginning of the file"""
        self.csvfile.seek(0)

        # skip header row
        self.csvfile.__next__()

    def num_columns(self):
        """gets the number of columns for the file"""
        return len(self.csvreader.fieldnames)

    @property
    def headers(self):
        """original ordered list of headers with leading and trailing spaces stripped"""
        return [entry.strip() for entry in self.csvreader.fieldnames]


class MCMParser(object):
    """
    This Parser is a wrapper around CSVReader and ExcelParser which matches
    columnar data against a set of known ontologies and separates data
    according to those distinctions.

    Map: mapping the columns to known ontologies, then colating data by these.
    Clean: coerce data according to ontology schema.
    Merge: merging the data from multiple sources into one ontology.

    usage:
            f = open('data.csv', 'rb')
            reader = MCMParser(f)
            rows = reader.next()
            for row in rows:
                # something with the row dict
            ...
            reader.seek_to_beginning()
            # rows.next() will return the first row

    """

    def __init__(self, import_file, sheet_name=None, *args, **kwargs):
        self.reader = self._get_reader(import_file, sheet_name)
        self.seek_to_beginning()

        self.import_file = import_file
        if 'matching_func' not in kwargs:
            # Special note, contains expects arguments like the following
            # contains(a, b); tests outcome of ``b in a``
            self.matching_func = operator.contains

        else:
            self.matching_func = kwargs.get('matching_func')

    def _get_reader(self, import_file, sheet_name=None):
        """returns a CSV or XLS/XLSX reader or raises an exception"""
        try:
            return ExcelParser(import_file, sheet_name)
        except XLRDError as e:
            if 'Unsupported format' in str(e):
                return CSVParser(import_file)
            else:
                raise Exception('Cannot parse file')

    def __next__(self):
        """calls the reader's next"""
        # TODO: Do i need to switch between csvreader and excelreader?
        return self.data.__next__()

    def seek_to_beginning(self):
        """calls the reader's seek_to_beginning"""
        if isinstance(self.reader, CSVParser):
            self.data = self.reader.csvreader
        elif isinstance(self.reader, ExcelParser):
            self.data = self.reader.excelreader
        else:
            raise Exception('Uknown type of parser in MCMParser')

        return self.reader.seek_to_beginning()

    def num_columns(self):
        """returns the number of columns of the file"""
        return self.reader.num_columns()

    @property
    def headers(self):
        """original ordered list of spreadsheet headers that are not cleaned"""
        return self.reader.headers

    @property
    def first_five_rows(self):
        """
        Return the first five rows of the file. This handles items with carriage returns in the
        field.

        :return: list of rows with ROW_DELIMITER
        """
        self.seek_to_beginning()

        validation_rows = []
        for i in range(5):
            try:
                row = self.__next__()
                if row:
                    # Trim out the spaces around the keys
                    new_row = {}
                    for k, v in row.items():
                        new_row[k.strip()] = v
                    validation_rows.append(new_row)
            except StopIteration:
                """Less than 5 rows in file"""
                break

        # return the first row of the headers which are cleaned
        first_row = self.headers

        tmp = []
        for r in validation_rows:
            row_arr = []
            for x in first_row:
                row_field = r[x]
                if isinstance(row_field, basestring):
                    row_field = unidecode(r[x])
                else:
                    row_field = str(r[x])
                row_arr.append(row_field.strip())

            tmp.append(ROW_DELIMITER.join(row_arr))

        self.seek_to_beginning()

        return tmp
