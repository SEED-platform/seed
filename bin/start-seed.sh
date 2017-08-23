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
    celery -A seed worker -l info -c 4 --maxtasksperchild 1000 --events > /tmp/celeryd.log 2>&1 &
else
    printf "Celery is already running\n"
fi

# Django standalone server
running "manage.py runserver"
if [ $? -eq 0 ]; then
    printf "Starting Django standalone server\n"
    ./manage.py runserver 0.0.0.0:8000 --settings=config.settings.dev
else
    printf "Django server is already running\n"
fi
