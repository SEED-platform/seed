#!/bin/bash

cd /seed

echo "Waiting for postgres to start"
/usr/local/wait-for-it.sh --strict -t 0 db-postgres:5432

echo "Waiting for redis to start"
/usr/local/wait-for-it.sh --strict -t 0 db-redis:6379

echo "Waiting for web to start"
/usr/local/wait-for-it.sh --strict -t 0 web:80

export WORKERS=$(($(nproc) * 2))
export WORKERS=$(($WORKERS>1?$WORKERS:1))
echo "Number of workers will be set to: $WORKERS"
celery -A seed worker -l info -c $WORKERS --maxtasksperchild 1000 --events
