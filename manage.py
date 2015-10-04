#!/usr/bin/env python
"""
:copyright: (c) 2014 Building Energy Inc
"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.main")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
