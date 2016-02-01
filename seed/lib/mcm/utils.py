# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from itertools import islice, chain

from dateutil import parser


def batch(iterable, size):
    """Generator to return iterators of size ``size``.

    :param iterable: any iterable type, items you need batched up.
    :param size: int, batch size.
    :rtype: iterable or lists.

    """
    sourceiter = iter(iterable)
    while 1:
        batchiter = islice(sourceiter, size)
        yield list(chain([batchiter.next()], batchiter))


def date_str_to_date(date_str):
    if date_str:
        return parser.parse(date_str)


def load_ontology(filename):
    """Load json structure from a file."""
    with open(filename, 'rb') as f:
        return json.loads(f.read())
