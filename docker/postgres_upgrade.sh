#!/bin/bash

echo "Starting upgrade of SEED database from Postgres 12 to Postgres 14..."

docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.pgupgrade.yml up -d
# docker-compose up -d db-postgres

echo "Waiting for PostgreSQL to start..."
# Wait until PostgreSQL starts and is ready to accept connections.
until docker-compose exec -T db-postgres pg_isready -U seed -d seed > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done

POSTGRES_VERSION=$(docker-compose exec -T db-postgres psql --user=seed -d postgres -t -A -c 'SHOW server_version;' | cut -d ' ' -f1)
TIMESCALE_VERSION=$(docker-compose exec -T db-postgres psql --user=seed -d postgres -t -A -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';")


echo "Disconnecting all other users from the 'seed' database..."
docker-compose exec -T db-postgres psql --user=seed -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'seed';"
export PG12_DUMP="/share/seed-pg${POSTGRES_VERSION}-${TIMESCALE_VERSION}-$(date +%Y%m%d%H%M%S).dump"
echo "Creating PostgresV: ${POSTGRES_VERSION} TimescaleV: ${TIMESCALE_VERSION} dump file of $PG12_DUMP..."
docker-compose exec -T db-postgres pg_dump --username=seed --dbname=seed --verbose --no-owner --no-acl -Z7 -Fc -f "${PG12_DUMP}"


echo "============================================"
echo "Starting PostgreSQL 13 Initialization Process"
echo "============================================"
echo "Waiting for PostgreSQL 13 to start..."
# Wait until PostgreSQL starts and is ready to accept connections.
until docker-compose exec -T seed-pg13 pg_isready -U seed -d seed > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done

echo
echo "PostgreSQL 13 is up and running."
echo

echo "Checking initial PostgreSQL and TimescaleDB versions for PostgreSQL 13..."
# Show PostgreSQL version
docker-compose exec -T seed-pg13 psql --user=seed -d postgres -c 'SELECT version();'

# Show TimescaleDB version
docker-compose exec -T seed-pg13 psql --user=seed -d postgres -c '\dx timescaledb'

echo "Setting up database and extensions on PostgreSQL 13..."
# Now, attempt to drop the 'seed' database
docker-compose exec -T seed-pg13 psql --user=seed -d postgres -c 'DROP DATABASE IF EXISTS "seed";'

# Create the "seed" database with the owner "seed"
docker-compose exec -T seed-pg13 psql --user=seed -d postgres -c 'CREATE DATABASE "seed" WITH OWNER = "seed";'

# Grant all privileges on the "seed" database to the user "seed"
docker-compose exec -T seed-pg13 psql --user=seed -c 'GRANT ALL PRIVILEGES ON DATABASE "seed" TO "seed";'

# Alter the user "seed" to have CREATEDB, CREATEROLE, and SUPERUSER privileges
docker-compose exec -T seed-pg13 psql --user=seed -c 'ALTER USER "seed" CREATEDB CREATEROLE SUPERUSER;'

# Create the PostGIS extension if it does not exist
docker-compose exec -T seed-pg13 psql --user=seed -d seed -c 'CREATE EXTENSION IF NOT EXISTS postgis;'

echo "Dropping TimescaleDB extension to prepare for reinstallation or update..."
# Drop the TimescaleDB extension
docker-compose exec -T seed-pg13 psql --user=seed -d seed -c "DROP EXTENSION timescaledb;"

echo "Pausing to ensure all database operations have ceased before proceeding..."
# Wait a moment (optional, might be needed in very fast consecutive executions)
sleep 10

echo "Creating the TimescaleDB extension with the specified version..."
# Create the extension
docker-compose exec -T seed-pg13 psql --user=seed -d seed -c "CREATE EXTENSION IF NOT EXISTS timescaledb WITH VERSION '2.3.0';"

echo "Verifying the TimescaleDB extension is installed correctly..."
# Check the extension
docker-compose exec -T seed-pg13 psql --user=seed -d seed -c '\dx timescaledb'

echo "Preparing the database for restore operations..."
docker-compose exec -T seed-pg13 psql --user=seed -d seed -c 'SELECT timescaledb_pre_restore();'

# Restore from backup
echo "Restoring postgres 12 database ${PG12_DUMP} from backup..."
docker-compose exec -T seed-pg13 pg_restore --exit-on-error --no-owner --no-acl --user=seed -d seed -v ${PG12_DUMP}

echo "Performing post-restore operations for TimescaleDB..."
# Post restore with TimescaleDB
docker-compose exec -T seed-pg13 psql --user=seed -d seed -c 'SELECT timescaledb_post_restore();'

echo "Verifying the TimescaleDB extension post-restore..."
# Check the extension again
docker-compose exec -T seed-pg13 psql --user=seed -d seed -c '\dx timescaledb'

echo "Updating TimescaleDB extension to ensure it's at the latest compatible version..."
docker-compose exec -T seed-pg13 psql --user=seed -d seed -c 'ALTER EXTENSION timescaledb UPDATE;'

# Capture the PostgreSQL version from the container
POSTGRES_VERSION=$(docker-compose exec -T seed-pg13 psql --user=seed -d postgres -t -A -c 'SHOW server_version;' | cut -d ' ' -f1)

# Capture the TimescaleDB version from the container using SQL command
TIMESCALE_VERSION=$(docker-compose exec -T seed-pg13 psql --user=seed -d postgres -t -A -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';")
export PG13_DUMP="/share/seed-pg${POSTGRES_VERSION}-${TIMESCALE_VERSION}-$(date +%Y%m%d%H%M%S).dump"
echo "Dumping upgraded Postgres Version: ${POSTGRES_VERSION}, TimescaleDB Version: ${TIMESCALE_VERSION} to file: ${PG13_DUMP}..."
docker-compose exec -T seed-pg13 pg_dump --username=seed --dbname=seed --verbose --no-owner --no-acl -Z7 -Fc -f "${PG13_DUMP}"


echo "============================================"
echo "Transitioning to PostgreSQL 14"
echo "============================================"

echo "Waiting for PostgreSQL 14 to start..."
# Wait until PostgreSQL 14 starts and is ready to accept connections.
until docker-compose exec -T seed-pg14 pg_isready -U seed -d seed > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done

echo
echo "PostgreSQL 14 is up and running."
echo

echo "Checking initial PostgreSQL and TimescaleDB versions for PostgreSQL 14..."
# Show PostgreSQL version
docker-compose exec -T seed-pg14 psql --user=seed -d postgres -c 'SELECT version();'

# Show TimescaleDB version
docker-compose exec -T seed-pg14 psql --user=seed -d postgres -c '\dx timescaledb'

echo "Setting up database and extensions on PostgreSQL 14..."

# Now, attempt to drop the 'seed' database
docker-compose exec -T seed-pg14 psql --user=seed -d postgres -c 'DROP DATABASE IF EXISTS "seed";'

# Create the "seed" database with the owner "seed"
docker-compose exec -T seed-pg14 psql --user=seed -d postgres -c 'CREATE DATABASE "seed" WITH OWNER = "seed";'

# Grant all privileges on the "seed" database to the user "seed"
docker-compose exec -T seed-pg14 psql --user=seed -c 'GRANT ALL PRIVILEGES ON DATABASE "seed" TO "seed";'

# Alter the user "seed" to have CREATEDB, CREATEROLE, and SUPERUSER privileges
docker-compose exec -T seed-pg14 psql --user=seed -c 'ALTER USER "seed" CREATEDB CREATEROLE SUPERUSER;'

# Create the PostGIS extension if it does not exist
docker-compose exec -T seed-pg14 psql --user=seed -d seed -c 'CREATE EXTENSION IF NOT EXISTS postgis;'

# Prepare for restore with TimescaleDB
docker-compose exec -T seed-pg14 psql --user=seed -d seed -c 'SELECT timescaledb_pre_restore();'

echo "Restoring postgres 13 database ${PG13_DUMP} from backup..."
# Restore from backup
docker-compose exec -T seed-pg14 pg_restore --exit-on-error --no-owner --no-acl --user=seed -d seed -v ${PG13_DUMP}

# Capture the PostgreSQL version from the containerP
POSTGRES_VERSION=$(docker-compose exec -T seed-pg14 psql --user=seed -d postgres -t -A -c 'SHOW server_version;' | cut -d ' ' -f1)
TIMESCALE_VERSION=$(docker-compose exec -T seed-pg14 psql --user=seed -d postgres -t -A -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';")
export PG14_DUMP="/share/seed-pg${POSTGRES_VERSION}-${TIMESCALE_VERSION}-$(date +%Y%m%d%H%M%S).dump"
echo "Dumping upgraded PostgresV: ${POSTGRES_VERSION} TimescaleV: ${TIMESCALE_VERSION} file of $PG14_DUMP..."
docker-compose exec -T seed-pg14 pg_dump --username=seed --dbname=seed --verbose --no-owner --no-acl -Z7 -Fc -f "${PG14_DUMP}"

export COMPOSE_FILE=docker-compose.pgupgrade.yml
docker-compose stop seed-pg13
docker-compose stop seed-pg14
unset COMPOSE_FILE
echo "Database operations completed."
