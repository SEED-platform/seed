#!/bin/bash

cd /seed

export WORKERS=$(($(nproc) * 2))
export WORKERS=$(($WORKERS>1?$WORKERS:1))
celery -A seed worker -l info -c $WORKERS -B --maxtasksperchild 1000 --events
