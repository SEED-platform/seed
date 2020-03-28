# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from seed import models
from seed.models import ASSESSED_RAW


def get_source_type(import_file, source_type=''):
    """Used for converting ImportFile source_type into an int."""

    # TODO: move source_type to a database lookup. Right now it is hard coded
    source_type_str = getattr(import_file, 'source_type', '') or ''
    source_type_str = source_type or source_type_str
    source_type_str = source_type_str.upper().replace(' ', '_')

    return getattr(models, source_type_str, ASSESSED_RAW)
