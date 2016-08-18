# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA

This module defines the functionality needed to create Page objects.

A Page object is a way of representing the page being tested separately from
the unit test, and contains methods that the unit test can use to interact
with that page, and the elements it contains.

A Page object needs to be supplied a web driver (browser instance) on
initialization: this is done by passing a Test Case instance (that inherits
from a class defined in base.py). This is done so Page objects can also
utilize some of its other functionality and attributes, as well as the
browser instance.

Note a Page object should not  *directly* contain any functionality necessary
to set up the page, e.g. database interactions. These methods remain with the
Test Case classes defined in base.py. However they may be accessed by classes
that subclass Page by calling the test_obj method so that subclasses can
handle setting up a page. Since creating a building snapshot is so common
there is a create_building method provided by Page.

:Example:

Sub Classing Page
=================

This is the preferred method and should be used any time a page will be
used in multiple tests.

Defining the page object
------------------------

class Home(Page):
    def __init__(self, test_obj):
        url = "index.html"
        locator = Locator('NAME', 'my-button')
        super(Home, self).__init__(test_obj, locator, url=url)
        self.load_page()

.. warning::
    a locator must be defined and passed to super(Class, self).__init__

Calling the page object in a test
---------------------------------
::
    from seed.functional.tests.browser_definitions import import BROWSERS
    from seed.functional.tests.base import LOGGED_IN_CLASSES
    from seed.functional.tests.pages import Home


    def my_tests_generator():
        for browser in BROWSERS:

            class Tests((LOGGED_OUT_CLASSES[browser.name]):

            def my_test(self):
                home_page = Home(self)
                my_element = home_page.find_element_by_name('example')
                assert my_element.text = 'example text'

:Example:

Sub Classing the Page Object for a page with a table
====================================================
class Home(Page):
    def __init__(self, test_obj):
        url = "index.html"
        locator = Locator('NAME', 'my-button')
        # will cause ensure_table_is_loaded method to be added
        self.table_locator = Locator('XPATH', '//table')
        super(Home, self).__init__(test_obj, locator, url=url)
        self.load_page()

Calling the page object in a test
---------------------------------
::
    from seed.functional.tests.browser_definitions import import BROWSERS
    from seed.functional.tests.base import LOGGED_IN_CLASSES
    from seed.functional.tests.pages import Home


    def my_tests_generator():
        for browser in BROWSERS:

            class Tests((LOGGED_OUT_CLASSES[browser.name]):

            def my_test(self):
                home_page = Home(self)
                table = home.page.ensure_table_is_loaded()
                assert table[0][0].text = 'example text'

:Example:

Calling Page directly
=====================
::
    from seed.functional.tests.browser_definitions import import BROWSERS
    from seed.functional.tests.base import LOGGED_IN_CLASSES
    from seed.functional.tests.page import Locator, Page


    def my_tests_generator():
        for browser in BROWSERS:

            class Tests((LOGGED_OUT_CLASSES[browser.name]):

            def my_test(self):
                url = "{}/home.html".format(self.live_server_url)
                my_locator = Locator('NAME', 'my-button')
                my_page = Page(self, my_locator, url=url)
                my_page.load_page()
                my_element = my_page.find_element_by_name('example')
                assert my_element.text = 'example text'

                # loads the next page, so we don't need a url
                my_element.click()
                my_other_locator = Locator('IF', 'my-id')
                my_other_page = Page(self, my_locator)
                my_other_element = my_other_page.find_element_by_id('example')
                assert my_other_element.text = 'example text'

:author Paul Munday<paul@paulmunday.net>
"""
import collections
import time

from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located
)
from selenium.webdriver.support.wait import WebDriverWait


STRATEGIES = {
    'CLASS_NAME': By.CLASS_NAME,
    'CSS_SELECTOR': By.CSS_SELECTOR,
    'ID': By.ID,
    'LINK_TEXT': By.LINK_TEXT,
    'NAME': By.NAME,
    'PARTIAL_LINK_TEXT': By.PARTIAL_LINK_TEXT,
    'TAG_NAME': By.TAG_NAME,
    'XPATH': By.XPATH,
}


Locator = collections.namedtuple('Locator', ['strategy', 'search_term'])
Imports = collections.namedtuple('Imports', ['import_file', 'import_record'])
Organization = collections.namedtuple('Organization', ['org', 'sub_orgs'])


class Page(object):
    """
    A web page under test,
    :param: locator: Locator object used to identify page
    :param: url: if True load by url, if False assume page is loaded
    :param: timeout: time out in seconds
    :param: use_text: if a string is supplied its value will be checked on locator


    :tpye: locator: Locator object
    :type: url: Bool or string, if string append to self.url.
    :type: timeout: int or float
    :type: use_text: string

    """
    ensure_table_is_loaded = None               # conditional method

    def __init__(self, test_obj, locator, url=None, timeout=None, use_text=None):
        self.test_obj = test_obj
        self.browser = test_obj.browser
        self.locator = locator
        self.use_text = use_text
        self.url = None
        if isinstance(url, str):
            self.url = "{}/".format(self.test_obj.live_server_url)
            if url != '/':
                self.url = self.url + url
        self.timeout = 15 if not timeout else timeout
        self.action = self.test_obj.get_action_chains()

        # Conditionally add method if self.table_locator is defined
        # this nees to happed in subclass __init__ methods
        # before super(Class, self)__init__()  is called
        if getattr(self, 'table_locator', None):
            if not getattr(self, 'ensure_table_is_loaded', None):
                self.ensure_table_is_loaded = self.__ensure_table_is_loaded

    def load_page(self):
        # load page if url is supplied.
        # If not it is assumed the page is already loaded by other means.
        # e.g. by clicking on an element of another page.
        if self.url:
            self.browser.get(self.url)
        return self._wait_for_page()

    def reload(self):
        """
        Reload the page if the browser has navigated away.
        i.e. another Page instance has been created.

        .. warning::

            This method does not navigate back to the page.
            You will need to do so yourself in your test. e.g. by
            locating and clicking on a suitable link.

            It is not possible to reliably use self.browser.get(self.url)
            as get() watches for the page onload event and this does not
            happen on many pages as page loads are effectively overwritten
            as an ajax call once the page has been loaded the first time.
        """
        return self._wait_for_page()

    def wait_for_element(self, strategy, search, timeout=None):
        """
        Get a page element, allowing time for the page to load.

        :returns WebElement.
        """
        if not timeout:
            timeout = self.timeout
        return WebDriverWait(self.browser, timeout).until(
            presence_of_element_located(
                (STRATEGIES[strategy], search)
            )
        )

    def wait_for_element_by_class_name(self, selector, timeout=15):
        """
        Get a page element by class name, allowing time for the page to load.

        :returns WebElement.
        """
        return self.wait_for_element('CLASS_NAME', selector, timeout=timeout)

    def wait_for_element_by_css(self, selector, timeout=15):
        return self.wait_for_element_by_css_selector(selector, timeout)

    def wait_for_element_by_css_selector(self, selector, timeout=15):
        """
        Get a page element by css, allowing time for the page to load.

        :returns WebElement.
        """
        return self.wait_for_element('CSS_SELECTOR', selector, timeout=timeout)

    def wait_for_element_by_id(self, selector, timeout=15):
        """
        Get a page element by id, allowing time for the page to load.

        :returns WebElement.
        """
        return self.wait_for_element('ID', selector, timeout=timeout)

    def wait_for_element_by_link_text(self, selector, timeout=15):
        """
        Get a page element by link_test, allowing time for the page to load.

        :returns WebElement.
        """
        return self.wait_for_element('LINK_TEXT', selector, timeout=timeout)

    def wait_for_element_by_partial_link_text(self, selector, timeout=15):
        """
        Get a page element by partial_link_test, allowing time for the page to load.

        :returns WebElement.
        """
        return self.wait_for_element('PARTIAL_LINK_TEXT', selector, timeout=timeout)

    def wait_for_element_by_tag_name(self, selector, timeout=15):
        """
        Get a page element by tag name, allowing time for the page to load.

        :returns WebElement.
        """
        return self.wait_for_element('tag_name', selector, timeout=timeout)

    def wait_for_element_by_xpath(self, selector, timeout=15):
        """
        Get a page element by xpath, allowing time for the page to load.

        :returns WebElement.
        """
        return self.wait_for_element('XPATH', selector, timeout=timeout)

    def _wait_for_page(self):
        """
        Allow time for the page to load.
        """
        # some pages cant be uniquely identified by locator, in these instance
        # setting use_text can be used to  cause the returned element to be checked
        # for presence of the text
        if self.use_text:
            # set a reasonable of times to try before timing out
            # if locator is not found in will timeout after self.timeout
            # if its found and the text doesn't match it will wait 500ms
            # then try again until it finds it or gives up
            tries = int(self.timeout)
            found = False
            for t in range(tries):
                locator = self.wait_for_element(
                    self.locator.strategy,
                    self.locator.search_term
                )
                try:
                    if locator.text == self.use_text:
                        found = True
                        break
                    else:
                        time.sleep(0.5)
                # page has refreshed
                except StaleElementReferenceException:
                    locator = self.wait_for_element(
                        self.locator.strategy,
                        self.locator.search_term
                    )
                    if locator.text == self.use_text:
                        found = True
                        break
            if not found:
                msg = (
                    "Found element using strategy {} with {}"
                    " but inner text {} did not match {}".format(
                        self.locator.strategy, self.locator.search_term,
                        locator.text, self.use_text
                    )
                )
                raise TimeoutException(msg=msg)
        else:
            locator = self.wait_for_element(
                self.locator.strategy,
                self.locator.search_term
            )
        return locator

    def create_record(self, create_building=False, import_record=None,
                      import_file=None, building=None):
        """
        Set up an import/building snapshot in the db.

        Pass dictionaries to import_file, import_record and building to set
        additional attributes. e.g. import_record= {'name': 'Name'} can be used
        to set the import record/data set name.

        As ImportFile.file is a django.db.models.FileField field it can be tricky
        to manipulate/mock. Use mock_file_factory from base.py to generate a mock_file
        and add it to the import_file dict. This will be added after the record is
        created and can be used to set the file name etc.

        :param create_building: create a building snapshot
        :param: import_record:  define additional attributes of the import record
        :param import_file: define additional attributes of the import file
        :param building: define additional attributes of the building snapshot

        :type: create_building: Bool
        :type: import_record: dict
        :type: import_file: dict
        :type: building: dict
        """
        canonical_building = None
        building = building if isinstance(building, dict) else {}
        import_record = import_record if isinstance(import_record, dict) else {}
        import_file = import_file if isinstance(import_file, dict) else {}

        import_record = self.test_obj.create_import_record(**import_record)
        import_file = self.test_obj.create_import_file(
            import_record, **import_file
        )

        if create_building or building:
            canonical_building = self.test_obj.create_building(
                import_file, **building
            )

        imports = Imports(import_file, import_record)
        return imports, canonical_building

    def create_project(self, name=None, building=None):
        """
        Create a project (and project building). If no building is supplied
        self.canonical_building will be used if present.

        :param: name: project name
        :param: :building: canonical building

        :type: name: string
        :type: building: CanonicalBuilding instance

        """
        building = building if building else getattr(
            self, 'canonical_building', None
        )
        project, project_building = self.test_obj.create_project(
            name=name, building=building
        )
        return project, project_building

    def get_canonical_building(self, id=None):
        """
        Get canonical building, by id or associated with Page,
        (self.canonical_building)

        :param: id: building id/CanonicalBuilding primary key
        :type: id: int

        :returns: CanonicalBuilding instance or None

        """
        if id:
            canonical_building = self.test_obj.get_canonical_building(id)
        else:
            canonical_building = getattr(self, 'canonical_building', None)
        return canonical_building

    def generate_buildings(self, num, import_file=None, building_details=None):
        """Create multiple buildings."""
        import_file = import_file if import_file else getattr(
            self, 'import_file')
        building_details = building_details if isinstance(
            building_details, dict) else {}
        self.test_obj.generate_buildings(num, import_file, **building_details)

    # Find element convenience methods
    # these just reflect the underlying browser methods
    def find_element_by_id(self, idstr):
        return self.browser.find_element_by_id(idstr)

    def find_elements_by_id(self, idstr):
        return self.browser.find_elements_by_id(idstr)

    def find_element_by_name(self, name):
        return self.browser.find_element_by_name(name)

    def find_elements_by_name(self, name):
        return self.browser.find_elements_by_name(name)

    def find_element_by_xpath(self, xpath):
        return self.browser.find_element_by_xpath(xpath)

    def find_elements_by_xpath(self, xpath):
        return self.browser.find_elements_by_xpath(xpath)

    def find_element_by_link_text(self, text):
        return self.browser.find_element_by_link_text(text)

    def find_elements_by_link_text(self, text):
        return self.browser.find_elements_by_link_text(text)

    def find_element_by_partial_link_text(self, text):
        return self.browser.find_element_by_partial_link_text(text)

    def find_elements_by_partial_link_text(self, text):
        return self.browser.find_elements_by_partial_link_text(text)

    def find_element_by_tag_name(self, name):
        return self.browser.find_element_by_tag_name(name)

    def find_elements_by_tag_name(self, name):
        return self.browser.find_elements_by_tag_name(name)

    def find_element_by_class_name(self, name):
        return self.browser.find_element_by_class_name(name)

    def find_elements_by_class_name(self, name):
        return self.browser.find_elements_by_class_name(name)

    def find_element_by_css_selector(self, selector):
        return self.browser.find_element_by_css_selector(selector)

    def find_elements_by_css_selector(self, selector):
        return self.browser.find_elements_by_css_selector(selector)

    # Action convenience methods
    # these just reflect the underlying browser/action chain methods
    def click(self, on_element=None):
        return self.action.click(on_element=on_element)

    def click_and_hold(self, on_element=None):
        return self.action.click_and_hold(on_element=on_element)

    def context_click(self, on_element=None):
        return self.action.context_click(on_element=on_element)

    def double_click(self, on_element=None):
        return self.action.double_click(on_element=on_element)

    def drag_and_drop(self, source, target):
        return self.action.drag_and_drop(source, target)

    def drag_and_drop_by_offset(self, source, xoffset, yoffset):
        return self.action.drag_and_drop_by_offset(source, xoffset, yoffset)

    def key_down(self, value, element=None):
        return self.action.key_down(value, element=element)

    def key_up(self, value, element=None):
        return self.action.key_up(value, element=element)

    def move_by_offset(self, xoffset, yoffset):
        return self.action.move_by_offset(xoffset, yoffset)

    def move_to_element(self, to_element):
        return self.action.move_to_element(to_element)

    def move_to_element_with_offset(self, to_element, xoffset, yoffset):
        return self.action.move_to_element_with_offset(
            to_element, xoffset, yoffset
        )

    def perform(self):
        self.action.perform()

    def perform_stored_actions(self):
        self.perform()

    def release(self, on_element=None):
        return self.action.release(on_element=on_element)

    def send_keys(self, *keys_to_send):
        self.action.send_keys(*keys_to_send)

    def send_keys_to_element(self, element, *keys_to_send):
        self.action.send_keys_to_element(element, *keys_to_send)

    # Scipt etc convenience methods
    # these just reflect the underlying browser methods

    def execute_async_script(self, script, *args):
        return self.browser.execute_async_script(script, *args)

    def execute_script(self, script, *args):
        return self.browser.execute_script(script, *args)

    def set_script_timeout(self, time_to_wait):
        self.browser.set_script_timeout(time_to_wait)

    def delete_all_cookies(self):
        self.browser.delete_all_cookies()

    def delete__cookie(self, name):
        self.browser.delete_cookie(name)

    def refresh(self):
        self.browser.refresh()

    def __ensure_table_is_loaded(self):
        """
        If a page contains a table ensure it is loaded.

        This is conditionally added as a method if self.table_locator is defined
        and there ensure_table_is_loaded is not (e.g is a method on the sub class)

        Don't try and call this directly. If you wish to override this define
        ensure_table_is_loaded in the sub class and this will not be used.

        :returns: the table as a Table object.

        """
        table_element = self.wait_for_element(
            self.table_locator.strategy,
            self.table_locator.search_term
        )
        return table_factory(table_element)


class Table(object):
    """
    Provides a convenient way to query/compare a table.

    :param: headers: Table headers
    :param: rows: Table rows
    :param: safe: if True raise an exception if number of columns and headers differs

    :type: headers: Sequence (list, tuple etc)
    :type: rows: Sequence of sequences/TableRows/OrderedDicts
    :type: safe: bool

    :Example:

    +----------+------+------------+
    | Food     | Cost $ | Quantity |
    +==========+========+==========+
    |Bananas   |  1     | 20       |
    +----------+--------+----------+
    |Apples    |  0.5   | 10       |
    +----------+--------+----------+
    |Pears     |  0.8   | 20       |
    +----------+--------+----------+

    >>> table = MyPage.ensure_table_is_loaded()
    >>> print table.headers
    ['Food', 'Cost', Quantity']
    >>> print table[1]
    {'Food': 'Apples', 'Cost': '0.5', 'Quantity: '10'}
    >>> print table[1]['Food'].text
    'Apples'
    >>> print table[1][0].text
    'Apples'
    >>> print table.first_row
    {'Food': 'Bananas', 'Cost': '1', 'Quantity: '20'}
    >>> print table.first_row['Food'].text
    Bananas
    >>> print table.last_row
    {'Food': 'Pears', 'Cost': '0.8', 'Quantity: '20'}
    >>> print table.column(0)
    ('Food', ['Bananas', 'Apples', 'Pears'])
    >>> print table.column(0).header_text
    Food
    >>> print table.column(0)[0].text
    Bananas
    >>> print table.column('Food')
    ('Food', ['Bananas', 'Apples', 'Pears'])
    >>> print len(table)
    3
    >>> print len(table.first_row)
    3
    >>> table.first_row.values()
    ['Bananas', '1', '20']
    >>> table.first_row.keys()
    ['Food', 'Cost', Quantity']
    >>> for key, val in table.first_row.items():
        >>>    print "{} = {}".format(key, val)
    Food = Bananas etc.
    >>> table.find_row_by_field('Food', 'Bananas')
    {'Food': 'Bananas', 'Cost': '1', 'Quantity: '20'}
    >>> table.find_row_by_field('Food', 'Limes')
    Noneed/functional/tests/page.py
    >>> table.find_rows_by_field(0, 'Bananas')
    [{'Food': 'Bananas', 'Cost': '1', 'Quantity: '20'}]
    >>> table.find_rows_by_field('Food', 'Bananas')
    [{'Food': 'Bananas', 'Cost': '1', 'Quantity: '20'}]
    >>> expected = Table(
        ['Food', 'Cost', Quantity'],
        [['Bananas', '1', '20'], ['Pears, 0.8, 20]]
    )
    >>> print expected.first_row
        {'Food': 'Bananas', 'Cost': '1', 'Quantity: '20'}
    >>> expected.first_row == table.first_row
    True
    >>> expected == table
    False
    >>> table.first_row in expected
    True
    >>> table[1] in expected
    False
    >>> {'Food': 'Apples', 'Cost': '0.5', 'Quantity': '10'} in table
    True
    >>> [row for row in table]
    [TableRow({'Food': 'Bananas', 'Cost': '1', 'Quantity: '20'})...]

    Instantiating:
    Typically you use the page objects ensure_table_is_loaded() method
    to load the page::
    >>> table = MyPage.ensure_table_is_loaded()

    This does the equivalent of this::
    >>> table_web_element = year_ending = page.find_element_by_xpath("//table")
    >>> table = table_factory(table_web_element, webdriver)

    You can also instantiate it directly, if, for instance you have a lot of
    values you want to test against::

        from collections import OrderedDict
        table = Table(
            ['Food', 'Cost', Quantity'],
            OrderedDict({'Food': 'Bananas', 'Cost': '1', 'Quantity: '20'})
        )

    Tuples or lists can be used.
    OK::

        Table(
        ["col 1", "col 2", "col 3"],
        [
            [1, 2, 3],
            [4, 5, 6]
        ]
        Table(
            ["a", "b]",
            [
                TableRow(OrderedDict({'a': 0, 'b': 1})),
                OrderedDict({'a': 2, 'b': 3}),
                TableRow([('a', 4), ('b':5)]
            ]
        )

    .. warning::

        This is probably not what you want::

            Table(
                ["a", "b]",
                [[('a', 1), ('b':2)], [('a', 4), ('b':5)]]
            )

        Equivalent to::

            Table(
                ["a", "b]",
                [
                    TableRow(OrderedDict({
                        'a': [('a', 1), ('b':2)]
                        'b': [('a', 4), ('b':5)]
                    })
                ]
            )

    """
    def __init__(self, headers, rows, safe=True):
        self.safe = safe
        self.headers = tuple([str(header) for header in headers])
        self.rows = self._get_rows(rows)

    def _get_rows(self, rows):
        _rows = []
        error = TypeError('Rows must be sequences, TableRows or OrderedDicts')
        _check_seq(rows, error)
        for row in rows:
            if isinstance(row, (TableRow, collections.OrderedDict)):
                _row = TableRow(row)
                if self.safe and sorted(_row.keys()) != sorted(self.headers):
                    raise KeyError(
                        "Keys in {} do not match {}".format(row, self.headers)
                    )
            elif _check_seq(row, error):
                if self.safe and len(row) != len(self.headers):
                    raise IndexError(
                        "{} does not contain the same number of elements "
                        "as {}".format(row, self.headers)
                    )
                # check types of row members
                types = set([
                    isinstance(val, collections.Sequence) and not
                    isinstance(val, basestring) for val in row
                ])
                if len(types) > 1:
                    raise TypeError("{} contains mixed types".format(row))
                # row is a sequence of sequences
                if True in types:
                    if self.safe:
                        for seq in row:
                            if len(seq) != 2:
                                raise IndexError(
                                    "{} from {} has the wrong length".format(
                                        seq, row
                                    )
                                )
                        keys = [seq[0] for seq in row]
                        if tuple(keys) != self.headers:
                            raise KeyError(
                                "Keys from  {} would not match {}".format(
                                    row, self.headers
                                )
                            )
                    _row = TableRow(row)
                # row is a plain sequence
                else:
                    _row = TableRow(
                        [
                            (self.headers[idx], val)
                            for idx, val in enumerate(row)
                        ]
                    )
            _rows.append(_row)
        return tuple(_rows)

    def __getitem__(self, idx):
        return self.rows[idx]

    def __len__(self):
        return len(self.rows)

    def __eq__(self, other):
        if not isinstance(other, Table):
            msg = "{} is not an instance of Table".format(other)
            raise TypeError(msg)
        return self.headers == other.headers and self.rows == other.rows

    def __contains__(self, val):
        val = TableRow(val)
        return val in self.rows

    def __iter__(self):
        self._itercount = 0
        return self

    def next(self):
        if self._itercount < len(self.rows):
            self._itercount += 1
            return self.rows[self._itercount - 1]
        else:
            raise StopIteration

    @property
    def first_row(self):
        return self.rows[0]

    @property
    def last_row(self):
        return self.rows[-1]

    def column(self, idx):
        """
        Return a table column corresponding to idx header,

        A table column is always returned if a column exists, but its values
        are set to None where row[idx] is not present.

        An index error will be raised if column corresponding to idx
        is not present.
        """
        error_msg = "{} is not a column or out of range".format(idx)
        if isinstance(idx, int):
            try:
                name = self.headers[idx]
            except IndexError:
                raise IndexError(error_msg)
        else:
            name = idx
            if name not in self.headers:
                raise IndexError(error_msg)
        return TableColumn(name, [row.get(name, None) for row in self.rows])

    def find_rows_by_field(self, idx, value):
        """
        Returns all rows where row[idx].text = value, or an empty list

        :param: idx: index of column/cell or column name
        :param: value: return rows whose text matches this value

        :type: idx: int/string
        :type: value: string

        """
        error_msg = "{} is not a column or out of range".format(idx)
        if isinstance(idx, int):
            try:
                name = self.headers[idx]
            except IndexError:
                raise IndexError(error_msg)
        else:
            name = idx
            if name not in self.headers:
                raise IndexError(error_msg)
        return [
            row for row in self.rows if row.get(name, None).text == value
        ]

    def find_row_by_field(self, idx, value):
        """
        Returns first row where row[idx].text = value, or None

        :param: idx: index of column/cell or column name
        :param: value: return rows whose text matches this value

        :type: idx: int/string
        :type: value: string

        """
        error_msg = "{} is not a column or out of range".format(idx)
        if isinstance(idx, int):
            try:
                name = self.headers[idx]
            except IndexError:
                raise IndexError(error_msg)
        else:
            name = idx
            if name not in self.headers:
                raise IndexError(error_msg)
        for row in self.rows:
            if row.get(name, None).text == value:
                return row
        return None


def table_factory(table):
    """
    Constructs a Table instance from a table web element.

    It can be difficult to locate elements in tables in selenium, unless
    you have a name or id. Typically you would have to locate e.g. a table cell
    by using an XPath. These can be long and difficult to figure out
    since you need to locate row and column by a number corresponding
    to their position and this is difficult to figure out since the
    table structure can vary.

    This avoids this issue by taking a table Web Element and then examining
    if for table headers. Based on what it finds in iterates through the
    table rows and converts these into ordered dictionaries where the key is the
    value of the table header and the value is the Web Element that represents
    the corresponding table cell.Where possible it tries to determine the
    table_header  by examining the inner text contained in a  header cell.
    If it is unable to do so it will instead use Col_0 etc

    :returns: instance of Table

    """
    safe = True
    table_header = table.find_elements_by_tag_name('thead')
    table_body = table.find_elements_by_tag_name('tbody')
    if not table_body:
        table_body = table
    else:
        # assume real body is last
        table_body = table_body[-1]
    rows = table_body.find_elements_by_tag_name('tr')
    if table_header:
        header_row = None
        # assume real head is last
        table_header = table_header[-1]
        header_rows = table_header.find_elements_by_tag_name('tr')
        # assume the row we want is the first one with the same length as the body
        row_length = len(rows[-1].find_elements_by_tag_name('td'))
        for row in header_rows:
            header_row_length = len(row.find_elements_by_tag_name('th'))
            if header_row_length == row_length:
                header_row = row
                break
        if not header_row:
            #  assume its the last
            safe = False
            # more headers than cells is ok
            if header_row_length > row_length:
                header_row = header_rows[-1]
            # fewer headers than cells is not ok
            else:
                raise IndexError("body row length > number of headers")

    else:
        # assume the row we want is the first
        header_row = rows[0]
        # discard the first row if it contains column names
        rows = rows[1:]
    headerlist = header_row.find_elements_by_tag_name('th')
    if headerlist:
        headers = [
            header.text if header.text else "Col_{}".format(idx)
            for idx, header in enumerate(headerlist)
        ]
    else:
        headers = ["Col_{}".format(i) for i in range(len(header_row))]
    rows = [row.find_elements_by_tag_name('td') for row in rows]
    return Table(headers, rows, safe=safe)


class TableRow(collections.Mapping):
    """
    TableRow is an immutable variant of an OrderedDict whose values can
    also be accessed by index (i.e. as if they were a list) when an int
    is supplied.

    In order to achieve this all key values are coerced to strings.
    While it will take numbers as keys in order to access them using [key]
    you must supply key as a string. However .get() performs the same
    coercion so e.g. .get(1) will work with the caveat that an error will
    not be raised if the key is not found.

    In order to prevent accidental clobbering of keys a KeyError will be
    raised if the number of keys is not the same as that supplied.
    i.e. TableRow({'1', 1, 1: 2}) will throw an error. However
    TableRow({'a': 1, 'a': 2}) will also throw an error, where creating a dict
    of the same would result in {'a': 2}.

    :Example:

    >>> tr = TableRow(OrderedDict({'a': 0, 'b': 1}))
    >>> tr['a']
    0
    >>> tr[0]
    0
    >>> tr
    TableRow({'a': 0, 'b': 1})
    >>> tr = TableRow([(1, 2), ('2', 3)])
    >>> tr['2']
    3
    >>> tr[0]
    2
    >>> tr[1]
    3
    >>> tr.get(1)
    2
    >>> tr.get(3)
    None
    >>> tr = TableRow({'a': 0, 'a': 1})
    KeyError
    >>> tr = TableRow([(2, 2), ('2', 3)])
    KeyError
    """
    def __init__(self, constructor, **kwargs):
        if isinstance(constructor, (TableRow, collections.OrderedDict)):
            key_check = len(constructor)
            constructor = [
                (str(key), constructor[key]) for key in constructor
            ]
        elif self._check_seq(constructor):
            key_check = len(constructor)
            constructor = [
                (str(item[0]), item[1]) for item in constructor
                if self._check_seq(item)
            ]
        self.__dict = collections.OrderedDict(constructor, **kwargs)
        if len(self.__dict) != key_check:
            raise KeyError("Key coercion collision.")

    def _check_seq(self, seq):
        errmsg = (
            "Invalid syntax, TableRow takes mapping objects (dict like)\n"
            "or sequences that contain list or tuple like objects only."
        )
        error = SyntaxError(errmsg)
        return _check_seq(seq, error)

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self.__dict.values()[idx]
        else:
            return self.__dict[idx]

    def get(self, key, *args):
        default = args[0] if args else None
        return self.__dict.get(str(key), default)

    def __iter__(self):
        return iter(self.__dict)

    def __len__(self):
        return len(self.__dict)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, dict(self.__dict))

    def __contains__(self, val):
        return val in self.__dict

    def __eq__(self, comp):
        return self.__dict == comp

    def __ne__(self, comp):
        return self.__dict != comp


class TableColumn(collections.Sequence):
    """
    An immutable sequence to represent a table column.
    The table header is stored in the table attribute.

    Comparisons:
    Header is not compared with comparisons.
    All comparisons are coerced to tuples so you can compare against any seq.

    Examples::
    >>> col0 = TableColumn('cost', [1,2,3])
    >>> col0.header
    cost
    >>> 1 in col0
    True
    >>> col0 == (1, 2, 3)
    True
    >>> col0 == [1, 2, 3]
    True
    >>> col1 = TableColumn('price', [1,2,3])
    >>> col0 == col1
    True
    >>> col0 == col1 and coll0.header == col1.header
    False
    """
    def __init__(self, header, elements=None):
        if not elements:
            elements = ()
        error = AttributeError('elements must be supplied as a sequence')
        _check_seq(elements, error)
        if not isinstance(header, basestring):
            raise AttributeError('header must be a string')
        self.header = header
        self.elements = tuple(elements)

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)

    def __contains__(self, val):
        return val in self.elements

    def __getitem__(self, idx):
        return self.elements[idx]

    def __repr__(self):
        return '{}({}, {})'.format(
            self.__class__.__name__, self.header, self.elements
        )

    def __eq__(self, comp):
        return self.elements.__eq__(tuple(comp))

    def __le__(self, comp):
        return self.elements.__le__(tuple(comp))

    def __ge__(self, comp):
        return self.elements.__ge__(tuple(comp))

    def __lt__(self, comp):
        return self.elements.__lt__(tuple(comp))

    def __gt__(self, comp):
        return self.elements.__gt__(tuple(comp))

    def __ne__(self, comp):
        return self.elements.__ne__(tuple(comp))


def _check_seq(seq, error):
        if (isinstance(seq, collections.Sequence) and not
                isinstance(seq, basestring)):
            return seq
        else:
            raise error
