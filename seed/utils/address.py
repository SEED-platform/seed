# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import re

import usaddress
# from past.builtins import basestring
from streetaddress import StreetAddressFormatter


def _normalize_subaddress_type(subaddress_type):
    subaddress_type = subaddress_type.lower().replace('.', '')
    map = {
        'bldg': 'building',
        'blg': 'building',
    }
    if subaddress_type in map:
        return map[subaddress_type]
    return subaddress_type


def _normalize_occupancy_type(occupancy_id):
    occupancy_id = occupancy_id.lower().replace('.', '')
    map = {
        'ste': 'suite',
        'suite': 'suite',
    }
    if occupancy_id in map:
        return map[occupancy_id]
    return occupancy_id


def _normalize_address_direction(direction):
    direction = direction.lower().replace('.', '')
    direction_map = {
        'east': 'e',
        'west': 'w',
        'north': 'n',
        'south': 's',
        'northeast': 'ne',
        'northwest': 'nw',
        'southeast': 'se',
        'southwest': 'sw'
    }
    if direction in direction_map:
        return direction_map[direction]
    return direction


POST_TYPE_MAP = {
    'avenue': 'ave',
}


def _normalize_address_post_type(post_type):
    value = post_type.lower().replace('.', '')
    return POST_TYPE_MAP.get(value, value)


ADDRESS_NUMBER_RE = re.compile((
    r''
    r'(?P<start>[0-9]+)'  # The left part of the range
    r'\s?'  # Optional whitespace before the separator
    r'[\\/-]?'  # Optional Separator
    r'\s?'  # Optional whitespace after the separator
    r'(?<=[\s\\/-])'  # Enforce match of at least one separator char.
    r'(?P<end>[0-9]+)'  # THe right part of the range
))


def _normalize_address_number(address_number):
    """
    Given the numeric portion of an address, normalize it.
    - strip leading zeros from numbers.
    - remove whitespace from ranges.
    - convert ranges to use dash as separator.
    - expand any numbers that appear to have had their leading digits
      truncated.
    """
    match = ADDRESS_NUMBER_RE.match(address_number)
    if match:
        # This address number is a range, so normalize it.
        components = match.groupdict()
        range_start = components['start'].lstrip("0")
        range_end = components['end'].lstrip("0")
        if len(range_end) < len(range_start):
            # The end range value is omitting a common prefix.  Add it back.
            prefix_length = len(range_start) - len(range_end)
            range_end = range_start[:prefix_length] + range_end
        return '-'.join([range_start, range_end])

    # some addresses have leading zeros, strip them here
    return address_number.lstrip("0")


def normalize_address_str(address_val):
    """
    Normalize the address to conform to short abbreviations.

    If an invalid address_val is provided, None is returned.

    If a valid address is provided, a normalized version is returned.
    """
    # if this string is empty the regular expression in the sa wont
    # like it, and fail, so leave returning nothing
    if not address_val:
        return None

    # if this is a byte string, then convert to a string-string
    if isinstance(address_val, bytes):
        address_val = address_val.decode('utf-8')
    elif not isinstance(address_val, str):
        address_val = str(address_val)
    else:
        pass

    # Do some string replacements to remove odd characters that we come across
    replacements = {
        '\xef\xbf\xbd': '',
        '\uFFFD': '',
    }
    for k, v in replacements.items():
        address_val = address_val.replace(k, v)

    # now parse the address into number, street name and street type
    try:
        # Add in the mapping of CornerOf to the AddressNumber.
        addr = usaddress.tag(str(address_val), tag_mapping={'CornerOf': 'AddressNumber'})[0]
    except usaddress.RepeatedLabelError:
        # usaddress can't parse this at all
        normalized_address = str(address_val)
    except UnicodeEncodeError:
        # Some kind of odd character issue that we are not handling yet.
        normalized_address = str(address_val)
    else:
        # Address can be parsed, so let's format it.
        normalized_address = ''

        if 'AddressNumber' in addr and addr['AddressNumber'] is not None:
            normalized_address = _normalize_address_number(
                addr['AddressNumber'])

        if 'StreetNamePreDirectional' in addr and addr['StreetNamePreDirectional'] is not None:
            normalized_address = normalized_address + ' ' + _normalize_address_direction(
                addr['StreetNamePreDirectional'])  # NOQA

        if 'StreetName' in addr and addr['StreetName'] is not None:
            normalized_address = normalized_address + ' ' + addr['StreetName']

        if 'StreetNamePostType' in addr and addr['StreetNamePostType'] is not None:
            # remove any periods from abbreviations
            normalized_address = normalized_address + ' ' + _normalize_address_post_type(
                addr['StreetNamePostType'])  # NOQA

        if 'StreetNamePostDirectional' in addr and addr['StreetNamePostDirectional'] is not None:
            normalized_address = normalized_address + ' ' + _normalize_address_direction(
                addr['StreetNamePostDirectional'])  # NOQA

        if 'SubaddressType' in addr and addr['SubaddressType'] is not None:
            normalized_address = normalized_address + ' ' + _normalize_subaddress_type(addr['SubaddressType'])  # NOQA

        if 'SubaddressIdentifier' in addr and addr['SubaddressIdentifier'] is not None:
            normalized_address = normalized_address + ' ' + addr['SubaddressIdentifier']

        if 'OccupancyType' in addr and addr['OccupancyType'] is not None:
            normalized_address = normalized_address + ' ' + _normalize_occupancy_type(addr['OccupancyType'])

        if 'OccupancyIdentifier' in addr and addr['OccupancyIdentifier'] is not None:
            normalized_address = normalized_address + ' ' + addr['OccupancyIdentifier']

        formatter = StreetAddressFormatter()
        normalized_address = formatter.abbrev_street_avenue_etc(normalized_address)

    return normalized_address.lower().strip()
