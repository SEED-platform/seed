#!/bin/bash

cd /seed

# Run any migrations before starting -- always
./manage.py migrate

WORKERS=$(($(nproc) / 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program /usr/local/bin/uwsgi --http 0.0.0.0:8000 --module wsgi \
    --max-requests 5000 --cheaper-initial 1 -p $WORKERS --single-interpreter --enable-threads \
    --wsgi-file /seed/config/wsgi.py
