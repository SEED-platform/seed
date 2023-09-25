"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import sys
# !/usr/bin/env python
# encoding: utf-8
from subprocess import call

c = call(['python manage.py compress --force'], stdout=open('/dev/null', 'w'), shell=True)
if c == 0:
    print("compression passed")
else:
    print("compression failed")

sys.exit(c)
