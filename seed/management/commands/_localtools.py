# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Nathan Addy

Helper methods for a couple (possibly deprecated) management tasks
"""


def write_to_file(msg):
    pass


def logging_info(msg):
    s = "INFO: {}".format(msg)
    print(s)
    write_to_file(s)


def get_core_organizations():
    # IDs of the 12 organizations defined by robin 6/6/16.
    # Google Doc for file describing this:
    # https://docs.google.com/document/u/4/d/1z1FScU-lysmgkCNGa9-hH0PCQudpzV_IG2IKcxYzyfM/edit
    # [69,20,156,49,7,10,181,117,105,126, 124,6]
    GOOD_ORGS = [20, 7, 49, 69, 10, 181, 156, 117, 124, 105, 126, 6]
    assert len(GOOD_ORGS) == 12
    return GOOD_ORGS
