"""
:copyright: (c) 2014 Building Energy Inc
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
from django.core.wsgi import get_wsgi_application
from dj_static import Cling
application = Cling(get_wsgi_application())
