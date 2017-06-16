#!/bin/bash

cd /seed

echo "Waiting for postgres to start"
/usr/local/wait-for-it.sh --strict -t 0 db-postgres:5432

echo "Waiting for redis to start"
/usr/local/wait-for-it.sh --strict -t 0 db-redis:6379

echo "Waiting for web to start"
/usr/local/wait-for-it.sh --strict -t 0 web:8000

export WORKERS=$(($(nproc) * 2))
export WORKERS=$(($WORKERS>1?$WORKERS:1))
celery -A seed worker -l info -c $WORKERS -B --maxtasksperchild 1000 --events
