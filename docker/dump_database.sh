#!/bin/bash

# Stop the script if an error occurs
set -e

echo "Checking initial PostgreSQL and TimescaleDB versions..."
# Show PostgreSQL version
docker-compose exec -T db-postgres psql --user=seed -d postgres -c 'SELECT version();'

# Show TimescaleDB version
docker-compose exec -T db-postgres psql --user=seed -d postgres -c '\dx timescaledb'

# Connect to the default 'postgres' database to disconnect all other users from the 'seed' database
docker-compose exec -T db-postgres psql --user=seed -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'seed';"

docker-compose exec -T db-postgres pg_dump --username=seed --dbname=seed --verbose --no-owner --no-acl -Z7 -Fc -f "/share/seed_$(date +%Y%m%d%H%M%S).dump"
