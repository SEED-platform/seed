# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author nicholas.long@nrel.gov

Methods to help with string parsing etc.
"""
from string import capwords


def titlecase(s):
    # Titlelize the display names correctly per python's documentation. Don't use .title()
    # https://docs.python.org/2/library/stdtypes.html#str.title
    return capwords(s.replace('_', ' '))
