"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
from django.core.wsgi import get_wsgi_application
from dj_static import Cling
application = Cling(get_wsgi_application())
