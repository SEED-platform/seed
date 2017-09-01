#!/bin/bash

cd /seed

echo "Waiting for postgres to start"
/usr/local/wait-for-it.sh --strict db-postgres:5432

echo "Waiting for redis to start"
/usr/local/wait-for-it.sh --strict db-redis:6379

# Run any migrations before starting -- always for now
./manage.py migrate
./manage.py create_default_user --username=$SEED_ADMIN_USER --password=$SEED_ADMIN_PASSWORD --organization=$SEED_ADMIN_ORG

WORKERS=$(($(nproc) / 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
/usr/local/bin/uwsgi --http 0.0.0.0:8000 --module wsgi --uid 1000 --gid 1000 \
    --max-requests 5000 --cheaper-initial 1 -p $WORKERS --single-interpreter --enable-threads \
    --wsgi-file /seed/config/wsgi.py

