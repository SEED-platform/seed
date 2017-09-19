# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

# methods to help with string parsing etc.

import re


def titlecase(s):
    # Titlelize the display names correctly per python's documentation. Don't use .title()
    # https://docs.python.org/2/library/stdtypes.html#str.title
    return re.sub(r"[A-Za-z]+('[A-Za-z]+)?",
                  lambda mo: mo.group(0)[0].upper() + mo.group(0)[1:].lower(), s).replace("_", " ")
