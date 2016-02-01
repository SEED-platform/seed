# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import regex

from django.db.models import Q

#
# For Reconciliation between data sets.
#

ADDRESS_REGEX = r'(\d*)(?:\s(\w+))+'


def break_up_address(address):
    """Return a list of strings, breaking up address num and st. name.

    "1232 Harris Blvd." -> [1232, ['Harris', 'Blvd.']]
    "23 SE Double Phantom St." -> [23, ['SE', 'Double' 'Phantom', 'St.']]

    """
    reg = regex.match(ADDRESS_REGEX, address)
    if not reg:
        # If we don't see any address information send on the street name.
        return None, address.split(' ')

    return reg.captures(1)[0], reg.captures(2)


def build_address_q(address, b_attr):
    """Build a Q(street number) AND (Q(street name) OR Q(quadrant)) Q object.

    :param address: str, the full address.
    :param b_attr: str, the attribute name you're going to query against.
    :rtype Q: Returns a Q object that queries for the street number
        and any other string data from the address field.

    """
    street_num, street_ids = break_up_address(address)
    address_q = Q()
    street_info_q = Q()
    if street_num:
        address_q = Q(**{'{0}__icontains'.format(b_attr): street_num})

    # Because we don't know which parts are omitted, we OR these.
    for street_id in street_ids:
        street_info_q |= Q(**{'{0}__icontains'.format(b_attr): street_id})

    # AND with the street number, which should probably be accurate.
    address_q &= street_info_q

    return address_q


# Mapping from PM data.
FIRST_PASS_PORTFOLIOMANAGERBUILDING = (
    ('property_name', 'property_name'),
    ((build_address_q, 'address_line_1'), 'address_line_1'),
    ('address_line_2', 'address_line_2'),

)

# Mapping from Assessor data.
FIRST_PASS_ASSESSEDBUILDING = (
    ('property_name', 'property_name'),
    ((build_address_q, 'address_line_1'), 'address_line_1'),
    ('address_line_2', 'address_line_2'),
)
