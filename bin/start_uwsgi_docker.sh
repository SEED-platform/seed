#!/bin/bash
cd /seed
source ./bin/docker_environment.sh

# This docker image expects seed to be at:


WORKERS=$(($(nproc) / 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program /usr/local/bin/uwsgi --http 0.0.0.0:8000 --module wsgi --max-requests 5000 --pidfile /var/run/uwsgi.pid --cheaper-initial 1 -p $WORKERS --single-interpreter --enable-threads
