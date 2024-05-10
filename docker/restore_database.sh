#!/bin/bash

echo "Checking initial PostgreSQL and TimescaleDB versions..."
# Show PostgreSQL version
docker-compose exec -T db-postgres psql --user=seed -d postgres -c 'SELECT version();'

# Show TimescaleDB version
docker-compose exec -T db-postgres psql --user=seed -d postgres -c '\dx timescaledb'

# Connect to the default 'postgres' database to disconnect all other users from the 'seed' database
docker-compose exec -T db-postgres psql --user=seed -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'seed';"

# Now, attempt to drop the 'seed' database
docker-compose exec -T db-postgres psql --user=seed -d postgres -c 'DROP DATABASE IF EXISTS "seed";'

# Create the "seed" database with the owner "seed"
docker-compose exec -T db-postgres psql --user=seed -d postgres -c 'CREATE DATABASE "seed" WITH OWNER = "seed";'

# Grant all privileges on the "seed" database to the user "seed"
docker-compose exec -T db-postgres psql --user=seed -c 'GRANT ALL PRIVILEGES ON DATABASE "seed" TO "seed";'

# Alter the user "seed" to have CREATEDB, CREATEROLE, and SUPERUSER privileges
docker-compose exec -T db-postgres psql --user=seed -c 'ALTER USER "seed" CREATEDB CREATEROLE SUPERUSER;'

# Create the PostGIS extension if it does not exist
docker-compose exec -T db-postgres psql --user=seed -d seed -c 'CREATE EXTENSION IF NOT EXISTS postgis;'

# Create the TimescaleDB extension if it does not exist
docker-compose exec -T db-postgres psql --user=seed -d seed -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;'

# Prepare for restore with TimescaleDB
docker-compose exec -T db-postgres psql --user=seed -d seed -c 'SELECT timescaledb_pre_restore();'

# Temporarily disable error stopping
set +e

# Restore from backup, using positional parameter $1 for the backup file path
docker-compose exec -T db-postgres pg_restore --no-owner --no-acl --user=seed -d seed -v < "$1"

# Re-enable error stopping
set -e

# Post restore with TimescaleDB
docker-compose exec -T db-postgres psql --user=seed -d seed -c 'SELECT timescaledb_post_restore();'

# Creating the PostGIS extension again in case needed in another database called "seeddb"
docker-compose exec -T db-postgres psql --user=seed -d seed -c "CREATE EXTENSION postgis;"

echo "Checking final PostgreSQL and TimescaleDB versions..."
# Show PostgreSQL version again
docker-compose exec -T db-postgres psql --user=seed -d postgres -c 'SELECT version();'

# Show TimescaleDB version again
docker-compose exec -T db-postgres psql --user=seed -d postgres -c '\dx timescaledb'

echo "Database operations completed."
