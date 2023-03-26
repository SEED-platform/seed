#!/bin/bash

WORKERS=$(($(nproc) * 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
celery -A seed beat -l INFO -S django_celery_beat.schedulers:DatabaseScheduler &
celery -A seed worker -l INFO -c $WORKERS --max-tasks-per-child 1000 -E
