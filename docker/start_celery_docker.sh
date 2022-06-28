#!/bin/bash

cd /seed

echo "Waiting for postgres to start"
/usr/local/wait-for-it.sh --strict -t 0 db-postgres:5432

echo "Waiting for redis to start"
/usr/local/wait-for-it.sh --strict -t 0 db-redis:6379

echo "Waiting for web to start"
/usr/local/wait-for-it.sh --strict -t 0 web:80

# check if the number of workers is set in the env
if [ -z ${NUMBER_OF_WORKERS} ]; then
    echo "env var for NUMBER_OF_WORKERS of celery is unset"
    # Set the number of workers to half the number of cores on the machine
    export NUMBER_OF_WORKERS=$(($(nproc) / 2))
    export NUMBER_OF_WORKERS=$(($NUMBER_OF_WORKERS>1?$NUMBER_OF_WORKERS:1))
fi

echo "Number of workers will be set to: $NUMBER_OF_WORKERS"
celery -A seed worker -l info -c $NUMBER_OF_WORKERS --max-tasks-per-child 1000 --uid 1000 --events
