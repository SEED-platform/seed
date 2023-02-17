#!/bin/bash

WORKERS=$(($(nproc) * 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
celery -A seed worker -l info -c $WORKERS --max-tasks-per-child=1000 --events -B --scheduler django_celery_beat.schedulers:DatabaseScheduler
