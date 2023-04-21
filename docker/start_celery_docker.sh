#!/bin/bash

cd /seed

echo "Waiting for postgres to start"
if [ -v POSTGRES_HOST ];
then
   POSTGRES_ACTUAL_HOST=$POSTGRES_HOST
else
   POSTGRES_ACTUAL_HOST=db-postgres
fi
/usr/local/wait-for-it.sh --strict -t 0 $POSTGRES_ACTUAL_HOST:$POSTGRES_PORT

echo "Waiting for redis to start"
if [ -v REDIS_HOST ];
then
    REDIS_ACTUAL_HOST=$REDIS_HOST
else
    REDIS_ACTUAL_HOST=db-redis
fi

/usr/local/wait-for-it.sh --strict -t 0 $REDIS_ACTUAL_HOST:6379

echo "Waiting for web to start"
if [ -v WEB_HOST ];
then
    WEB_ACTUAL_HOST=$WEB_HOST
else
    WEB_ACTUAL_HOST=web
fi

/usr/local/wait-for-it.sh --strict -t 0 $WEB_ACTUAL_HOST:80

# check if the number of workers is set in the env
if [ -z ${NUMBER_OF_WORKERS} ]; then
    echo "env var for NUMBER_OF_WORKERS of celery is unset"
    # Set the number of workers to half the number of cores on the machine
    export NUMBER_OF_WORKERS=$(($(nproc) / 2))
    export NUMBER_OF_WORKERS=$(($NUMBER_OF_WORKERS>1?$NUMBER_OF_WORKERS:1))
fi

echo "Number of workers will be set to: $NUMBER_OF_WORKERS"
celery -A seed beat -l INFO --uid 1000 -S django_celery_beat.schedulers:DatabaseScheduler &
celery -A seed worker -l INFO -c $NUMBER_OF_WORKERS --max-tasks-per-child 1000 --uid 1000 -E
