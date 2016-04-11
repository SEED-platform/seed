#!/bin/bash

WORKERS=$(($(nproc) / 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
/usr/local/bin/uwsgi --http 127.0.0.1:8000 --module wsgi --daemonize /home/ubuntu/uwsgi.log --max-requests 5000 --pidfile /tmp/uwsgi.pid --cheaper-initial 1 -p $WORKERS --single-interpreter --enable-threads --touch-reload /home/ubuntu/touch-reload
