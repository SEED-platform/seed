#!/bin/bash

cd /seed

echo "Waiting for postgres to start"
/usr/local/wait-for-it.sh --strict db-postgres:5432

echo "Waiting for redis to start"
/usr/local/wait-for-it.sh --strict db-redis:6379

# collect static resources before starting and compress the assets
./manage.py collectstatic --no-input
./manage.py compress --force

# Run any migrations before starting -- always for now
./manage.py migrate

echo "Creating default user"
./manage.py create_default_user --username=$SEED_ADMIN_USER --password=$SEED_ADMIN_PASSWORD --organization=$SEED_ADMIN_ORG

/usr/local/bin/uwsgi --ini /seed/docker/uwsgi.ini
