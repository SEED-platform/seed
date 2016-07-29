# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA

Tests for the functional test infrastructure, not the actual tests, thankfully.

:author Paul Munday<paul@paulmunday.net>
"""
from collections import OrderedDict
import mock
import unittest

import seed.functional.tests.page


class PageTests(unittest.TestCase):
    """Tests for the base Page class."""

    def setUp(self):
        self.test_obj = mock.MagicMock()
        self.browser = mock.MagicMock()
        self.test_obj.browser = self.browser
        self.test_obj.live_server_url = 'http://example.org'
        self.locator = seed.functional.tests.page.Locator('ID', 'test')

    def test_object_creation(self):
        url = 'test'
        page_obj = seed.functional.tests.page.Page(
            self.test_obj, self.locator, url=url, timeout=10, use_text='test'
        )

        assert page_obj.locator == self.locator
        assert page_obj.browser == self.browser
        assert page_obj.timeout == 10
        assert page_obj.use_text == 'test'
        assert page_obj.url == 'http://example.org/test'
        # assert test_obj.get_action_chains called
        assert self.test_obj.method_calls[0][0] == 'get_action_chains'

    @mock.patch.object(seed.functional.tests.page.Page, '_wait_for_page')
    def test_load_page(self, mock_wait_for_page):
        mock_wait_for_page.return_value = 'test'
        url = 'test'
        page_obj = seed.functional.tests.page.Page(
            self.test_obj, self.locator, url=url
        )
        page = page_obj.load_page()

        assert mock_wait_for_page.called
        self.browser.get.assert_called_with('http://example.org/test')
        assert page == 'test'

    @mock.patch.object(seed.functional.tests.page.Page, 'wait_for_element')
    def test__wait_for_page(self, mock_wait_for_element):
        mock_wait_for_element.return_value = 'fake element'
        page_obj = seed.functional.tests.page.Page(
            self.test_obj, self.locator
        )
        element = page_obj._wait_for_page()

        mock_wait_for_element.assert_called_with(
            self.locator.strategy, self.locator.search_term
        )
        assert element == 'fake element'

    @mock.patch.object(seed.functional.tests.page.Page, 'wait_for_element')
    def test__wait_for_page_with_use_text(self, mock_wait_for_element):
        mock_element = mock.MagicMock()
        mock_element.text = 'test'
        mock_wait_for_element.return_value = mock_element

        page_obj = seed.functional.tests.page.Page(
            self.test_obj, self.locator, use_text='test'
        )
        element = page_obj._wait_for_page()

        mock_wait_for_element.assert_called_with(
            self.locator.strategy, self.locator.search_term
        )
        assert element == mock_element

    def test_create_record(self):
        self.test_obj.create_import_record.return_value = 'test record'
        self.test_obj.create_import_file.return_value = 'test file'
        self.test_obj.create_building.return_value = 'test building'

        import_record = {'name': 'test'}
        import_file = {'name': 'test'}
        building = {'name': 'test'}
        page_obj = seed.functional.tests.page.Page(
            self.test_obj, self.locator
        )
        imports, canonical_building = page_obj.create_record(
            import_record=import_record,
            import_file=import_file,
            building=building
        )

        self.test_obj.create_import_record.assert_called_with(
            name='test'
        )
        self.test_obj.create_import_file.assert_called_with(
            'test record', name='test'
        )
        self.test_obj.create_building.assert_called_with(
            'test file', name='test'
        )
        assert isinstance(imports, seed.functional.tests.page.Imports)
        assert imports.import_file == 'test file'
        assert imports.import_record == 'test record'
        assert canonical_building == 'test building'

    def test_create_project(self):
        self.test_obj.create_project.return_value = (
            'test project', 'test project building'
        )
        page_obj = seed.functional.tests.page.Page(
            self.test_obj, self.locator
        )
        page_obj.canonical_building = 'test building'
        project, project_building = page_obj.create_project(name='test')

        self.test_obj.create_project.assert_called_with(
            name='test', building='test building'
        )
        assert project == 'test project'
        assert project_building == 'test project building'

    def test_get_canonical_building(self):
        self.test_obj.get_canonical_building.return_value = 'test'
        page_obj = seed.functional.tests.page.Page(
            self.test_obj, self.locator
        )

        canonical_building = page_obj.get_canonical_building()
        assert canonical_building is None

        page_obj.canonical_building = 'test building'
        canonical_building = page_obj.get_canonical_building()
        assert canonical_building == 'test building'

        canonical_building = page_obj.get_canonical_building(id=1)
        self.test_obj.get_canonical_building.assert_called_with(1)
        assert canonical_building == 'test'

    @mock.patch('seed.functional.tests.page.table_factory')
    @mock.patch.object(seed.functional.tests.page.Page, 'wait_for_element')
    def test_ensure_table_is_loaded_and_subclassing(
            self, mock_wait_for_element, mock_table_factory):
        mock_wait_for_element.side_effect = ['page', 'table']
        mock_table_factory.return_value = 'mock_table'
        table_locator = seed.functional.tests.page.Locator('XPATH', '//table')

        class TestPage(seed.functional.tests.page.Page):
            def __init__(self, test_obj, locator, table_locator):
                locator = locator
                self.table_locator = table_locator
                super(TestPage, self).__init__(test_obj, locator, url=None)
                self.page = self.load_page()

        page_obj = TestPage(self.test_obj, self.locator, table_locator)
        table = page_obj.ensure_table_is_loaded()

        call1 = mock.call(self.locator.strategy, self.locator.search_term)
        call2 = mock.call(table_locator.strategy, table_locator.search_term)
        expected_call_args = [call1, call2]
        assert mock_wait_for_element.call_args_list == expected_call_args
        mock_table_factory.assert_called_with('table')
        assert table == 'mock_table'


class TableColumnTests(unittest.TestCase):
    """Tests for the Table Column class."""

    def setUp(self):
        self.table_column = seed.functional.tests.page.TableColumn(
            'test', [1, 2, 3]
        )

    def test_equality(self):
        assert self.table_column.header == 'test'
        assert self.table_column.elements == (1, 2, 3)

        assert self.table_column == (1, 2, 3)
        assert self.table_column == [1, 2, 3]
        assert self.table_column[0] == 1
        assert self.table_column[-1] == 3
        assert self.table_column != [1, 2, 2]
        assert self.table_column != (1, 2, 2)
        assert self.table_column != [1, 2]

    def test_iterator(self):
        assert [i for i in self.table_column] == [1, 2, 3]

    def test_len(self):
        assert len(self.table_column) == 3

    def test_contains(self):
        for x in range(1, 4):
            assert x in self.table_column
        assert 0 not in self.table_column

    def test_comparison(self):
        assert self.table_column < [1, 2, 4]
        assert self.table_column <= [1, 2, 3]
        assert self.table_column <= [1, 2, 4]

        assert self.table_column > [1, 2, 2]
        assert self.table_column >= [1, 2, 3]
        assert self.table_column >= [1, 2, 2]

    def test_repr(self):
        assert str(self.table_column) == "TableColumn(test, (1, 2, 3))"


class TableRowTests(unittest.TestCase):
    """Tests for the Table Row class."""

    def setUp(self):
        self.table_row = seed.functional.tests.page.TableRow(
            [('a', 0), ('b', 1)]
        )

    def test_constructor(self):
        table_row_1 = seed.functional.tests.page.TableRow(
            [('a', 0), ('b', 1)]
        )
        table_row_2 = seed.functional.tests.page.TableRow(
            OrderedDict([('a', 0), ('b', 1)])
        )
        assert table_row_1 == table_row_2

        with self.assertRaises(SyntaxError):
            seed.functional.tests.page.TableRow(1)

        with self.assertRaises(KeyError):
            seed.functional.tests.page.TableRow(
                OrderedDict({'1': 0, 1: 1})
            )

    def test_getitem(self):
        assert self.table_row[0] == self.table_row['a'] == 0

    def test_get(self):
        assert self.table_row.get('a') == 0
        assert self.table_row.get('c') is None
        assert self.table_row.get('c', 2) == 2

    def test_iter(self):
        assert [i for i in self.table_row.keys()] == ['a', 'b']
        assert [i for i in self.table_row.values()] == [0, 1]
        assert [i for i in self.table_row.items()] == [('a', 0), ('b', 1)]

    def test_len(self):
        assert len(self.table_row) == 2

    def test_contains(self):
        assert 'a' in self.table_row

    def test_equality(self):
        assert self.table_row == {'b': 1, 'a': 0}
        assert self.table_row != {'a': 1, 'b': 0}


class TableTests(unittest.TestCase):
    """Tests for the Table class"""

    def setUp(self):
        self.table_row1 = seed.functional.tests.page.TableRow(
            [('a', 0), ('b', 1)]
        )
        self.table_row2 = seed.functional.tests.page.TableRow(
            [('a', 2), ('b', 3)]
        )
        self.table_row3 = seed.functional.tests.page.TableRow(
            [('a', 2), ('b', 3)]
        )
        self.table = seed.functional.tests.page.Table(
            ['a', 'b'], [self.table_row1, self.table_row2, self.table_row3]
        )

    def test_constructor(self):
        table_row1 = seed.functional.tests.page.TableRow([('a', 0), ('b', 1)])

        assert self.table.headers == ('a', 'b')
        assert len(self.table.rows) == 3
        assert self.table.rows == (
            self.table_row1, self.table_row2, self.table_row3
        )

        table = seed.functional.tests.page.Table(['a', 'b'], [[0, 1]])
        assert table.headers == ('a', 'b')
        assert table.rows == (table_row1,)

    def test__get_row_exceptions(self):
        table_row1 = seed.functional.tests.page.TableRow([('a', 0), ('b', 1)])
        table_row2 = seed.functional.tests.page.TableRow([('a', 2)])

        with self.assertRaises(KeyError):
            seed.functional.tests.page.Table(
                ['a', 'b'], [table_row1, table_row2]
            )

        with self.assertRaisesRegexp(
                IndexError, "does not contain the same number of elements"):
            seed.functional.tests.page.Table(
                ['a', 'b'], [[0, 1, 2]]
            )

        with self.assertRaisesRegexp(
                TypeError, 'Rows must be sequences, TableRows or OrderedDicts'):
            seed.functional.tests.page.Table(
                ['a', 'b'], [0, 1, 2]
            )

        with self.assertRaisesRegexp(
                TypeError, 'Rows must be sequences, TableRows or OrderedDicts'):
            seed.functional.tests.page.Table(
                ['a', 'b'], [0, (1, 2)]
            )

        with self.assertRaisesRegexp(TypeError, 'contains mixed type'):
            seed.functional.tests.page.Table(
                ['a', 'b'], [[0, (1, 2)]]
            )

        with self.assertRaisesRegexp(IndexError, "has the wrong length"):
            seed.functional.tests.page.Table(
                ['a', 'b'], [[(0, 1), [2]]]
            )

        with self.assertRaisesRegexp(KeyError, "would not match"):
            seed.functional.tests.page.Table(
                ['a', 'b'], [[(0, 1), [1, 2]]]
            )

    def test_getitem(self):
        assert self.table[0] == self.table_row1
        assert self.table[0][0] == 0
        assert self.table[0]['a'] == 0

    def test_len(self):
        assert len(self.table) == 3

    def test_equality(self):
        table_row1 = seed.functional.tests.page.TableRow([('a', 0), ('b', 1)])
        table_row2 = seed.functional.tests.page.TableRow([('a', 2), ('b', 3)])
        table_row3 = seed.functional.tests.page.TableRow([('a', 2), ('b', 3)])

        table = seed.functional.tests.page.Table(
            ['a', 'b'], [table_row1, table_row2, table_row3]
        )
        assert table == self.table

        table = seed.functional.tests.page.Table(
            ['a', 'b'], [table_row1, table_row2]
        )
        assert table != self.table

        with self.assertRaisesRegexp(TypeError, 'not an instance of Table'):
            table == 'foo'

    def test_comparison(self):
        table_row1 = seed.functional.tests.page.TableRow([('a', 0), ('b', 1)])
        table_row2 = seed.functional.tests.page.TableRow([('a', 7), ('b', 1)])

        assert table_row1 in self.table
        assert table_row2 not in self.table

    def test_iter(self):
        expected = [self.table_row1, self.table_row2, self.table_row3]
        assert [row for row in self.table] == expected

    def test_row_properties(self):
        assert self.table.first_row == self.table_row1
        assert self.table.last_row == self.table_row2

    def test_column(self):
        column = seed.functional.tests.page.TableColumn('a', [0, 2, 2])

        assert self.table.column('a') == column
        assert self.table.column(0) == column

        with self.assertRaisesRegexp(
                IndexError, 'not a column or out of range'):
            self.table.column('z')

        with self.assertRaisesRegexp(
                IndexError, 'not a column or out of range'):
            self.table.column(100)

    def test_find_row(self):
        element = mock.MagicMock()
        element.text = 'test'
        row = seed.functional.tests.page.TableRow([('a', element)])

        table = seed.functional.tests.page.Table(['a'], [[element], [element]])

        assert table.find_row_by_field('a', 'test') == row
        assert table.find_row_by_field(0, 'test') == row

        assert table.find_rows_by_field('a', 'test') == [row, row]
        assert table.find_rows_by_field(0, 'test') == [row, row]

        assert table.find_row_by_field('a', 'test1') is None
        assert table.find_row_by_field(0, 'test1') is None

        assert table.find_rows_by_field('a', 'test1') == []
        assert table.find_rows_by_field(0, 'test1') == []

        with self.assertRaisesRegexp(
                IndexError, 'not a column or out of range'):
            self.table.find_row_by_field('z', 'test')

        with self.assertRaisesRegexp(
                IndexError, 'not a column or out of range'):
            self.table.find_row_by_field(100, 'test')

        with self.assertRaisesRegexp(
                IndexError, 'not a column or out of range'):
            self.table.find_rows_by_field('z', 'test')

        with self.assertRaisesRegexp(
                IndexError, 'not a column or out of range'):
            self.table.find_rows_by_field(100, 'test')


class TestTableFactory(unittest.TestCase):

    def test_with_header_and_body(self):
        table = mock.MagicMock()
        table_head = mock.MagicMock()
        table_header = mock.MagicMock()
        header_row = mock.MagicMock()
        table_body = mock.MagicMock()
        table_row = mock.MagicMock()
        table_header.text = 'test'
        table.find_elements_by_tag_name.side_effect = [
            [table_head], [table_body]
        ]
        header_row.find_elements_by_tag_name.return_value = [table_header]
        table_head.find_elements_by_tag_name.return_value = [header_row]
        table_body.find_elements_by_tag_name.return_value = [table_row]
        table_row.find_elements_by_tag_name.return_value = ['test']

        table_obj = seed.functional.tests.page.table_factory(table)
        assert len(table_obj) == 1
        assert table_obj.headers == ('test', )
        assert table_obj[0]['test'] == 'test'
        assert table_obj[0][0] == 'test'

    def test_with_header_and_body_unsafe(self):
        table = mock.MagicMock()
        table_head = mock.MagicMock()
        table_header1 = mock.MagicMock()
        table_header2 = mock.MagicMock()
        header_row = mock.MagicMock()
        table_body = mock.MagicMock()
        table_row = mock.MagicMock()
        table_header1.text = 'test'
        table_header2.text = 'test2'
        table.find_elements_by_tag_name.side_effect = [
            [table_head], [table_body]
        ]
        header_row.find_elements_by_tag_name.return_value = [
            table_header1, table_header2
        ]
        table_head.find_elements_by_tag_name.return_value = [header_row]
        table_body.find_elements_by_tag_name.return_value = [table_row]
        table_row.find_elements_by_tag_name.return_value = ['test']

        table_obj = seed.functional.tests.page.table_factory(table)
        assert len(table_obj) == 1
        assert table_obj.headers == ('test', 'test2')
        assert table_obj[0]['test'] == 'test'
        assert table_obj[0][0] == 'test'
        with self.assertRaises(KeyError):
            table_obj[0]['test2']

    def test_with_header_and_body_very_unsafe(self):
        table = mock.MagicMock()
        table_head = mock.MagicMock()
        table_header = mock.MagicMock()
        header_row = mock.MagicMock()
        table_body = mock.MagicMock()
        table_row = mock.MagicMock()
        table_header.text = 'test'
        table.find_elements_by_tag_name.side_effect = [
            [table_head], [table_body]
        ]
        header_row.find_elements_by_tag_name.return_value = [table_header]
        table_head.find_elements_by_tag_name.return_value = [header_row]
        table_body.find_elements_by_tag_name.return_value = [table_row]
        table_row.find_elements_by_tag_name.return_value = ['test', 'test']

        with self.assertRaisesRegexp(IndexError, 'body row length'):
            seed.functional.tests.page.table_factory(table)

    def test_with_noheader(self):
        table = mock.MagicMock()
        table_body = mock.MagicMock()
        table_row = mock.MagicMock()
        table_element = mock.MagicMock()
        table_element.text = 'test'
        table.find_elements_by_tag_name.side_effect = [None, [table_body]]
        table_body.find_elements_by_tag_name.return_value = [
            table_row, table_row
        ]
        table_row.find_elements_by_tag_name.return_value = [table_element]

        table_obj = seed.functional.tests.page.table_factory(table)
        assert len(table_obj) == 1
        assert table_obj.headers == ('test', )
        assert table_obj[0]['test'].text == 'test'
        assert table_obj[0][0].text == 'test'

    def test_with_noheader_nobody(self):
        table = mock.MagicMock()
        table_row = mock.MagicMock()
        table_element = mock.MagicMock()
        table_element.text = 'test'
        table.find_elements_by_tag_name.side_effect = [
            None, None, [table_row, table_row]
        ]
        table_row.find_elements_by_tag_name.return_value = [table_element]

        table_obj = seed.functional.tests.page.table_factory(table)
        assert len(table_obj) == 1
        assert table_obj.headers == ('test', )
        assert table_obj[0]['test'].text == 'test'
        assert table_obj[0][0].text == 'test'
