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
import re
import string

from faker import Factory

from seed.models import BuildingSnapshot

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


class FakeBuildingSnapshotFactory(BaseFake):
    """
    Factory Class for producing Building Snaphots.
    """

    def __init__(self, super_organization=None, num_owners=5):
        super(FakeBuildingSnapshotFactory, self).__init__()
        self.super_organization = super_organization
        # pre-generate a list of owners so they occur more than once.
        self.owners = [self.owner() for i in range(num_owners)]

    def building_details(self):
        """Return a dict of pseudo random data for use with Building Snapshot"""
        owner = self.fake.random_element(elements=self.owners)
        return {
            'tax_lot_id': self.fake.numerify(text='#####'),
            'address_line_1': self.address_line_1(),
            'city': 'Boring',
            'state_province': 'Oregon',
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

    def building_snapshot(self, import_file, canonical_building,
                          super_organization=None, **kw):
        """Return a building snapshot populated with pseudo random data"""
        building_details = {
            'super_organization': self._get_attr('super_organization',
                                                 super_organization),
            'import_file': import_file,
            'canonical_building': canonical_building,
        }
        building_details.update(self.building_details())
        building_details.update(kw)
        return BuildingSnapshot.objects.create(**building_details)
