"""
:copyright: (c) 2014 Building Energy Inc
"""
#!/usr/bin/env python
# encoding: utf-8
from subprocess import call

c = call(['python manage.py compress --force'], stdout=open('/dev/null', 'w'), shell=True)
if c == 0:
    print "compression passed"
else:
    print "compression failed"

import sys
sys.exit(c)
