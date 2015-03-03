#!/bin/bash
# Start SEED in developer mode

# check if "$prog" is running
running () {
    prog="$1"
    #printf "Looking for '$prog'\n"
    n=$(/bin/ps auxw | grep -c "$prog")
    if [ $n -lt 2 ]; then
        ret=0
    else
        ret=1
    fi
    return $ret
}

# Redis
running redis
if [ $? -eq 0 ]; then
    printf "Starting Redis server\n"
    redis-server >/tmp/redis-server.log 2>&1 &
else
    printf "Redis is already running\n"
fi

# Celery
running celery
if [ $? -eq 0 ]; then
    printf "Starting Celery\n"
    ./manage.py celery worker -B -c 2 --loglevel=INFO -E \
        --maxtasksperchild=1000 >/tmp/celery.log 2>&1 &
else
    printf "Celery is already running\n"
fi

# Django standalone server
running "manage.py runserver"
if [ $? -eq 0 ]; then
    printf "Starting Django standalone server\n"
    ./manage.py runserver --settings=BE.settings.dev
else
    printf "Django server is already running\n"
fi