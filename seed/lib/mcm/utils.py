# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from itertools import islice, chain


def batch(iterable, size):
    """Generator to return iterators of size ``size``.

    :param iterable: any iterable type, items you need batched up.
    :param size: int, batch size.
    :rtype: iterable or lists.

    """
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        try:
            yield list(chain([batchiter.__next__()], batchiter))
        except StopIteration:
            return
