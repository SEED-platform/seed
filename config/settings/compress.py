"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author

    Used with django-compress to properly link relative links (i.e. image urls)
    within less files while compiling them to css files.
    `DEBUG` should be `True` to get compress to have the indented behavior.
    See bin/post_compile for current use.
    Example:
        ./manage compress --force --settings=config.settings.compress
"""
from __future__ import absolute_import

try:
    from config.settings.local_untracked import *  # noqa
except ImportError:
    pass
DEBUG = True
