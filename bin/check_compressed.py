"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
#!/usr/bin/env python
# encoding: utf-8
from subprocess import call

c = call(['python manage.py compress --force'], stdout=open('/dev/null', 'w'), shell=True)
if c == 0:
    print("compression passed")
else:
    print("compression failed")

import sys
sys.exit(c)
