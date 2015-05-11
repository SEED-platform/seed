"""
:copyright: (c) 2014 Building Energy Inc


The Reader module is intended to contain only code which reads data
out of CSV files. Fuzzy matches, application to data models happens
elsewhere.

"""
import datetime
import mmap
import operator
import sys

from unicodecsv import DictReader, Sniffer
import unicodedata
from xlrd import XLRDError, open_workbook, xldate_as_tuple

from mcm import mapper, utils

# from xlrd/biffh.py
(
    XL_CELL_EMPTY,
    XL_CELL_TEXT,
    XL_CELL_NUMBER,
    XL_CELL_DATE,
    XL_CELL_BOOLEAN,
    XL_CELL_ERROR,
    XL_CELL_BLANK,  # for use in debugging, gathering stats, etc
) = range(7)


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
        self.excel_file = excel_file
        self.sheet = self._get_sheet(excel_file)
        self.header_row = kwargs.pop('header_row', 0)
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

    def get_value(self, item, **kwargs):
        """Handle different value types for XLS.

        :param item: xlrd cell object
        :returns: items value with dates parsed properly
        """

        # Thx to Augusto C Men to point fast solution for XLS/XLSX dates
        if item.ctype == XL_CELL_DATE:
            return datetime.datetime(
                *xldate_as_tuple(item.value, self._workbook.datemode)
            )

        if item.ctype == XL_CELL_NUMBER:
            if item.value % 1 == 0:  # integers
                return int(item.value)
            else:
                return item.value

        if isinstance(item.value, unicode):
            return unicodedata.normalize('NFKD', item.value).encode(
                'ascii', 'ignore'
            )

        return item.value

    def XLSDictReader(self, sheet, header_row=0):
        """returns a generator yeilding a dict per row from the XLS/XLSX file
        https://gist.github.com/mdellavo/639082

        :param sheet: xlrd Sheet
        :param header_row: the row index to start with
        :returns: Generator yeilding a row as Dict
        """
        def item(i, j):
            """returns a tuple (column header, cell value)"""
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

    def next(self):
        """generator to match CSVReader"""
        while 1:
            try:
                yield self.excelreader.next()
            except StopIteration:
                break

    def seek_to_beginning(self):
        """seeks to the beginning of the file

        Since ``XLSDictReader`` is in memory, a new one is created
        """
        self.excel_file.seek(0)
        self.excelreader = self.XLSDictReader(self.sheet, self.header_row)

    def num_columns(self):
        """gets the number of columns for the file"""
        return self.sheet.ncols


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
    # Character escape sequences to replace
    CLEAN_SUPER = [u'\ufffd', u'\xb2']

    def __init__(self, csvfile, *args, **kwargs):
        self.csvfile = csvfile
        self.csvreader = self._get_csv_reader(csvfile, **kwargs)
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
            return DictReader(self.csvfile, errors='replace')

        else:
            reader_type = kwargs.get('reader_type')
            del kwargs['reader_type']
            return reader_type(self.csvfile, dialect, **kwargs)

    def _clean_super(self, col, replace=u'2'):
        """Cleans up various superscript unicode escapes.

        :param col: str, column name as read from the file.
        :param replace: (optional) str, string to replace superscripts with.
        :rtype: str, cleaned row name.

        """
        for item in self.CLEAN_SUPER:
            col = col.replace(item, unicode(replace))

        return col

    def clean_super_scripts(self):
        """Replaces column names with clean ones."""
        new_fields = []
        for col in self.csvreader.unicode_fieldnames:
            new_fields.append(self._clean_super(col))

        self.csvreader.unicode_fieldnames = new_fields

    def next(self):
        """Wouldn't it be nice to get iterables form csvreader?"""
        while 1:
            try:
                yield self.csvreader.next()
            except StopIteration:
                break

    def seek_to_beginning(self):
        """seeks to the beginning of the file"""
        self.csvfile.seek(0)
        # skip header row
        self.next().next()

    def num_columns(self):
        """gets the number of columns for the file"""
        return len(self.csvreader.unicode_fieldnames)


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
        self.import_file = import_file
        if 'matching_func' not in kwargs:
            # Special note, contains expects argumengs like the following
            # contains(a, b); tests outcome of ``b in a``
            self.matching_func = operator.contains

        else:
            self.matching_func = kwargs.get('matching_func')

    def split_rows(self, chunk_size, callback, *args, **kwargs):
        """Break up the CSV into smaller pieces for parallel processing."""
        row_num = 0
        for batch in utils.batch(self.next(), chunk_size):
            row_num += len(batch)
            callback(batch, *args, **kwargs)

        return row_num

    def map_rows(self, mapping, model_class):
        """Convenience method to call ``mapper.map_row`` on all rows.

        :param mapping: dict, keys map columns to model_class attrs.
        :param model_class: class, reference to model class.

        """
        for row in self.next():
            # Figure out if this is an inser or update.
            # e.g. model.objects.get('some canonical id') or model_class()
            yield mapper.map_row(row, mapping, model_class)

    def _get_reader(self, import_file):
        """returns a CSV or XLS/XLSX reader or raises an exception"""
        try:
            return ExcelParser(import_file)
        except XLRDError as e:
            if 'Unsupported format' in e.message:
                return CSVParser(import_file)
            else:
                raise Exception('Cannot parse file')

    def next(self):
        """calls the reader's next"""
        return self.reader.next()

    def seek_to_beginning(self):
        """calls the reader's seek_to_beginning"""
        return self.reader.seek_to_beginning()

    def num_columns(self):
        """returns the number of columns of the file"""
        return self.reader.num_columns()


def main():
    """Just some contrived test code."""
    from mcm.mappings import espm
    from mcm.tests.utils import FakeModel

    if len(sys.argv) < 2:
        sys.exit('You need to specify a CSV file path.')

    with open(sys.argv[1], 'rb') as f:
        parser = MCMParser(f)
        mapping = espm.MAP
        model_class = FakeModel
        for m in parser.map_rows(mapping, model_class):
            m.save()


if __name__ == '__main__':
    main()
