#!/bin/sh
set -x
export DJANGO_SETTINGS_MODULE=BE.settings.dev
export ONLY_HTTPS=False
cd /seed
python manage.py runserver 0.0.0.0:8000
