# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA

This files has faker methods for generating fake data.

The data is pseudo random, but still predictable. I.e. calling the same
method mutiple times will always return the same sequence of results
(after initialization)..

.. warning::

    Do not edit the seed unless you know what you are doing!

    .. codeauthor:: Paul Munday<paul@paulmunday.net>
"""
from collections import namedtuple
import datetime
import os
import re
import string

from faker import Factory
import mock

from django.db.models.fields.files import FieldFile

from seed.models import Cycle, Column, Property, PropertyState, TaxLotState


Owner = namedtuple(
    'Owner',
    ['name', 'email', 'telephone', 'address', 'city_state', 'postal_code']
)

SEED = 'f89ceea9-2162-4e7f-a3ed-e0b76a0513d1'

# For added realism
STREET_SUFFIX = (
    'Avenue', 'Avenue', 'Avenue', 'Boulevard', 'Lane', 'Loop',
    'Road', 'Road', 'Street', 'Street', 'Street', 'Street'
)


class BaseFake(object):
    """
    Base class for fake factories.

    .. warning::

    *Always* call super, *first* when overridding init if you subclass this.

    """
    def __init__(self):
        self.fake = Factory.create()
        self.fake.seed(SEED)

    def _check_attr(self, attr):
        result = getattr(self, attr, None)
        if not result:
            msg = "{} was not set on instance of: {}".format(
                attr, self.__class__
            )
            raise AttributeError(msg)
        return result

    def _get_attr(self, attrname, attr=None):
        attr = attr if attr else self._check_attr(attrname)
        return attr

    def address_line_1(self):
        return "{} {} {}".format(
            self.fake.randomize_nb_elements(1000),
            self.fake.last_name(),
            self.fake.random_element(elements=STREET_SUFFIX)
        )

    def owner(self, city=None, state=None):
        email = self.fake.company_email()
        ergx = re.compile('.*@(.*)\..*')
        company = "{} {}".format(
            string.capwords(ergx.match(email).group(1), '-').replace('-', ' '),
            self.fake.company_suffix()
        )
        return Owner(
            company, email, self.fake.phone_number(), self.address_line_1(),
            "{}, {}".format(city if city else self.fake.city(),
                            state if state else self.fake.state_abbr()),
            self.fake.postalcode()
        )


class FakeColumnFactory(BaseFake):
    """
    Factory Class for producing Column instances.
    """
    def __init__(self, organization=None):
        super(FakeColumnFactory, self).__init__()
        self.organization = organization

    def get_column(self, name, organization=None, is_extra_data=False,
                   extra_data_source=None, **kw):
        source = extra_data_source[0].upper() if extra_data_source else None
        if is_extra_data and not source or source not in ['P', 'T']:
            msg = (
                "extra_data_source must be one of P(property), T(axlot) "
                "if is_extra_data is True."
            )
            raise AttributeError(msg)
        elif source and not is_extra_data:
            raise AttributeError(
                "extra_data_source supplied but is_extra_data is False."
            )
        column_details = {
            'organization': organization if organization else self.organization,
            'column_name': name,
        }
        if is_extra_data:
            column_details.update({
                'is_extra_data': is_extra_data,
                'extra_data_source': source
            })
        column_details.update(kw)
        return Column.objects.create(**column_details)


class FakeCycleFactory(BaseFake):
    """
    Factory Class for producing Cycle instances.
    """

    def __init__(self, organization=None, user=None):
        super(FakeCycleFactory, self).__init__()
        self.organization = organization
        self.user = user

    def get_cycle(self, organization=None, user=None, **kw):
        start = self.fake.date_time_this_decade()
        start = datetime.datetime(start.year, 01, 01)
        end = start + datetime.timedelta(365)
        cycle_details = {
            'organization': getattr(self, 'organization', None),
            'user': getattr(self, 'user', None),
            'name': '{} Annual'.format(start.year),
            'start': start,
            'end': end,
        }
        cycle_details.update(kw)
        return Cycle.objects.create(**cycle_details)


class FakePropertyFactory(BaseFake):
    """
    Factory Class for producing Cycle instances.
    """

    def __init__(self, organization=None):
        super(FakePropertyFactory, self).__init__()
        self.organization = organization

    def get_property(self, organization=None, **kw):
        property_details = {
            'organization': self._get_attr('organization', organization),
        }
        property_details.update(kw)
        return Property.objects.create(**property_details)


class FakePropertyStateFactory(BaseFake):
    """
    Factory Class for producing PropertyState instances.
    """

    def __init__(self, num_owners=5):
        super(FakePropertyStateFactory, self).__init__()
        # pre-generate a list of owners so they occur more than once.
        self.owners = [self.owner() for i in range(num_owners)]

    def get_details(self):
        """Return a dict of pseudo random data for use with PropertyState"""
        owner = self.fake.random_element(elements=self.owners)
        return {
            'jurisdiction_property_identifier': self.fake.numerify(text='#####'),
            'pm_parent_property_id': self.fake.numerify(text='#####'),
            'lot_number': self.fake.numerify(text='#####'),
            'address_line_1': self.address_line_1(),
            'city': 'Boring',
            'state': 'Oregon',
            'postal_code': "970{}".format(self.fake.numerify(text='##')),
            'year_built': self.fake.random_int(min=1880, max=2015),
            'site_eui': self.fake.random_int(min=50, max=600),
            'owner': owner.name,
            'owner_email': owner.email,
            'owner_telephone': owner.telephone,
            'owner_address': owner.address,
            'owner_city_state': owner.city_state,
            'owner_postal_code': owner.postal_code,
        }

    def get_property_state(self, **kw):
        """Return a property state populated with pseudo random data"""
        property_details = self.get_details()
        property_details.update(kw)
        return PropertyState.objects.create(**property_details)


class FakeTaxLotStateFactory(BaseFake):
    """
    Factory Class for producing TaxLotState instances.
    """

    def get_taxlot_state(self, **kw):
        """Return a taxlot state populated with pseudo random data"""
        taxlot_details = {
            'jurisdiction_taxlot_identifier': self.fake.numerify(text='#####'),
            'block_number': self.fake.numerify(text='#####'),
            'address': self.address_line_1(),
            'city': 'Boring',
            'state': 'Oregon',
            'postal_code': "970{}".format(self.fake.numerify(text='##')),
        }
        taxlot_details.update(kw)
        return TaxLotState.objects.create(**taxlot_details)


def mock_file_factory(name, size=None, url=None, path=None):
    """
    This creates a mock instance of a FieldFile from
    django.db.models.fields.files.
    This is used to represent a file stored in Django and is linked file storage
    so it handles uploading and saving to disk.
    The mock allow you to set the file name etc without having to save a file to disk.
    """
    mock_file = mock.MagicMock(spec=FieldFile)
    mock_file._committed = True
    mock_file.file_name = name
    mock_file.name = name
    mock_file.base_name = os.path.splitext(name)[0]
    mock_file.__unicode__.return_value = name

    def __eq__(other):
        if hasattr(other, 'name'):
            return name == other.name
        else:
            return name == other
    mock_file.__eq__.side_effect = __eq__

    def __ne__(other):
        return not __eq__(other)

    mock_file.__ne__.side_effect = __ne__
    mock_file._get_size.return_value = size
    mock_size = mock.PropertyMock(return_value=size)
    type(mock_file).size = mock_size
    mock_file._get_path.return_value = path
    mock_path = mock.PropertyMock(return_value=path)
    type(mock_file).path = mock_path
    mock_file._get_url.return_value = url
    mock_url = mock.PropertyMock(return_value=url)
    type(mock_file).url = mock_url
    mock_file._get_closed.return_value = True
    mock_closed = mock.PropertyMock(return_value=True)
    type(mock_file).closed = mock_closed
    return mock_file
