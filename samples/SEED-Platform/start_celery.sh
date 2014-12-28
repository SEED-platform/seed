#!/bin/sh
set -x
source /vagrant/.virtualenvs/seed/bin/activate
cd /vagrant/seed
export DJANGO_SETTINGS_MODULE=BE.settings.dev
export ONLY_HTTPS=False
#cd /vagrant/~/mmc-seed
python manage.py celeryd
