"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author Nathan Addy
:description Helper methods for a couple (possibly deprecated) management tasks
"""


def write_to_file(msg):
    pass


def logging_info(msg):
    s = f"INFO: {msg}"
    print(s)
    write_to_file(s)


def get_core_organizations():
    # IDs of the 12 organizations defined by robin 6/6/16.
    # Google Doc for file describing this:
    # https://docs.google.com/document/u/4/d/1z1FScU-lysmgkCNGa9-hH0PCQudpzV_IG2IKcxYzyfM/edit
    # [69,20,156,49,7,10,181,117,105,126, 124,6]
    GOOD_ORGS = [20, 7, 49, 69, 10, 181, 156, 117, 124, 105, 126, 6]
    if len(GOOD_ORGS) != 12:
        raise ValueError("Invalid number of core organization ids")
    return GOOD_ORGS
