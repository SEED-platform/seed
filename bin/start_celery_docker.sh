#!/bin/bash

cd /seed

WORKERS=$(($(nproc) * 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
celery -A seed worker -l info -c $WORKERS \
    --maxtasksperchild 1000 --events
