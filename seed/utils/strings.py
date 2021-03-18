# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

# methods to help with string parsing etc.

from string import capwords


def titlecase(s):
    # Titlelize the display names correctly per python's documentation. Don't use .title()
    # https://docs.python.org/2/library/stdtypes.html#str.title
    return capwords(s.replace('_', ' '))
