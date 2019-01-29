# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
"""
The Reader module is intended to contain only code which reads data
out of CSV files. Fuzzy matches, application to data models happens
elsewhere.

"""
import mmap
import operator
from builtins import str
from csv import DictReader, Sniffer

from past.builtins import basestring
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

    def __init__(self, excel_file, *args, **kwargs):
        self.cache_headers = []
        self.excel_file = excel_file
        self.sheet = self._get_sheet(excel_file)
        self.header_row = self._get_header_row(self.sheet)
        self.excelreader = self.XLSDictReader(self.sheet, self.header_row)

    def _get_sheet(self, f, sheet_index=0):
        """returns a xlrd sheet

        :param f: an open file of type ``file``
        :param sheet_index: the excel sheet with a 0-index
        :returns: xlrd Sheet
        """
        data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        book = open_workbook(file_contents=data, on_demand=True)
        self._workbook = book  # needed to determine datemode
        return book.sheet_by_index(sheet_index)

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

    def __init__(self, import_file, *args, **kwargs):
        self.reader = self._get_reader(import_file)
        self.seek_to_beginning()

        self.import_file = import_file
        if 'matching_func' not in kwargs:
            # Special note, contains expects arguments like the following
            # contains(a, b); tests outcome of ``b in a``
            self.matching_func = operator.contains

        else:
            self.matching_func = kwargs.get('matching_func')

    def _get_reader(self, import_file):
        """returns a CSV or XLS/XLSX reader or raises an exception"""
        try:
            return ExcelParser(import_file)
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
