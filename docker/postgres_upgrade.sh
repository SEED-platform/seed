#!/bin/bash

# Initialize variables with default values for optional parameters
SOURCE_PG_CONV_VERSION='13'
SOURCE_TS_CONV_VERSION='2.14.2'
VERBOSE_MODE=false  # Default verbose mode is set to false

# Initialize variables for required parameters without default values
TARGET_PG_TEST_VERSION=""
TARGET_TS_TEST_VERSION=""

# Parse named command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --source-pg-conv-version)
            SOURCE_PG_CONV_VERSION="$2"
            shift 2
            ;;
        --source-ts-conv-version)
            SOURCE_TS_CONV_VERSION="$2"
            shift 2
            ;;
        --target-pg-test-version)
            TARGET_PG_TEST_VERSION="$2"
            shift 2
            ;;
        --target-ts-test-version)
            TARGET_TS_TEST_VERSION="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE_MODE=true
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--source-pg-conv-version <version>] [--source-ts-conv-version <version>] --target-pg-test-version <version> --target-ts-test-version <version> [--verbose]"
            exit 1
            ;;
    esac
done

# Check if any of the required variables are still empty
if [ -z "$TARGET_PG_TEST_VERSION" ] || [ -z "$TARGET_TS_TEST_VERSION" ]; then
    echo "Error: Missing required arguments."
    echo "Usage: $0 [--source-pg-conv-version <version>] [--source-ts-conv-version <version>] --target-pg-test-version <version> --target-ts-test-version <version> [--verbose]"
    exit 1
fi

# Print the variables to confirm they are set
echo "Source PostgreSQL Test Version: $SOURCE_PG_CONV_VERSION"
echo "Source Timescale Test Version: $SOURCE_TS_CONV_VERSION"
echo "Target PostgreSQL Test Version: $TARGET_PG_TEST_VERSION"
echo "Target Timescale Test Version: $TARGET_TS_TEST_VERSION"

PG_CONV_STRING="PostgreSQL ${SOURCE_PG_CONV_VERSION}"
PG_TEST_STRING="PostgreSQL ${TARGET_PG_TEST_VERSION}"

# Now print the values of these correctly named variables
echo "PG_CONV_STRING set to: $PG_CONV_STRING"
echo "PG_TEST_STRING set to: $PG_TEST_STRING"

echo "Starting standard docker-compose dev environment..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# set intermediary source conversion postgres container from docker-compose.pgupgrade.yml

# Assuming SOURCE_PG_CONV_VERSION and SOURCE_TS_CONV_VERSION have been defined earlier in the script
echo "Setting up conversion service name from source PostgreSQL and TimescaleDB versions..."
SOURCE_PG_TIMESCALE_CONV_SERVICE="pg${SOURCE_PG_CONV_VERSION}-${SOURCE_TS_CONV_VERSION}"
echo "Source PostgreSQL Timescale Conversion Service set to: $SOURCE_PG_TIMESCALE_CONV_SERVICE"

# Assuming TARGET_PG_TEST_VERSION and TARGET_TS_TEST_VERSION have been defined earlier in the script
echo "Setting up test service name from target PostgreSQL and TimescaleDB versions..."
TARGET_PG_TIMESCALE_TEST_SERVICE="pg${TARGET_PG_TEST_VERSION}-${TARGET_TS_TEST_VERSION}"
echo "Target PostgreSQL Timescale Test Service set to: $TARGET_PG_TIMESCALE_TEST_SERVICE"

# Start the specified Docker POSTGRES TIMESCALE TARGET SERVICE using docker-compose
echo "Starting the Docker services for PostgreSQL Timescale using docker-compose..."
docker-compose -f docker-compose.pgupgrade.yml up "${SOURCE_PG_TIMESCALE_CONV_SERVICE}" "${TARGET_PG_TIMESCALE_TEST_SERVICE}" -d
echo "Docker services started: ${TARGET_PG_TIMESCALE_TEST_SERVICE}, ${SOURCE_PG_TIMESCALE_CONV_SERVICE}"


echo "Starting upgrade of SEED database from Postgres 12 to $SOURCE_PG_TIMESCALE_CONV_SERVICE..."

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
# Execute pg_dump command with or without --verbose flag based on VERBOSE_MODE
if $VERBOSE_MODE; then
    docker-compose exec -T db-postgres pg_dump --username=seed --dbname=seed --verbose --no-owner --no-acl -Z7 -Fc -f "${PG12_DUMP}"
else
    docker-compose exec -T db-postgres pg_dump --username=seed --dbname=seed --no-owner --no-acl -Z7 -Fc -f "${PG12_DUMP}"
fi



echo "============================================"
echo "Starting ${PG_CONV_STRING} Initialization Process"
echo "============================================"
echo "Waiting for ${SOURCE_PG_TIMESCALE_CONV_SERVICE} to start..."
# Wait until PostgreSQL starts and is ready to accept connections.
until docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} pg_isready -U seed -d seed > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done

echo
echo "${PG_CONV_STRING} is up and running."
echo

echo "Checking initial PostgreSQL and TimescaleDB versions for ${PG_CONV_STRING}..."
# Show PostgreSQL version
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d postgres -c 'SELECT version();'

# Show TimescaleDB version
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d postgres -c '\dx timescaledb'

echo "Setting up database and extensions on ${PG_CONV_STRING}..."
# Now, attempt to drop the 'seed' database
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d postgres -c 'DROP DATABASE IF EXISTS "seed";'

# Create the "seed" database with the owner "seed"
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d postgres -c 'CREATE DATABASE "seed" WITH OWNER = "seed";'

# Grant all privileges on the "seed" database to the user "seed"
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -c 'GRANT ALL PRIVILEGES ON DATABASE "seed" TO "seed";'

# Alter the user "seed" to have CREATEDB, CREATEROLE, and SUPERUSER privileges
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -c 'ALTER USER "seed" CREATEDB CREATEROLE SUPERUSER;'

# Create the PostGIS extension if it does not exist
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d seed -c 'CREATE EXTENSION IF NOT EXISTS postgis;'

echo "Dropping TimescaleDB extension to prepare for reinstallation or update..."
# Drop the TimescaleDB extension
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d seed -c "DROP EXTENSION timescaledb;"

echo "Pausing to ensure all database operations have ceased before proceeding..."
# Wait a moment (optional, might be needed in very fast consecutive executions)
sleep 10

echo "Creating the TimescaleDB extension with the specified version..."
# Create the extension
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d seed -c "CREATE EXTENSION IF NOT EXISTS timescaledb WITH VERSION '${TARGET_TS_TEST_VERSION}' ;"

echo "Verifying the TimescaleDB extension is installed correctly..."
# Check the extension
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d seed -c '\dx timescaledb'

echo "Preparing the database for restore operations..."
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d seed -c 'SELECT timescaledb_pre_restore();'

# Restore from backup
echo "Restoring postgres 12 database ${PG12_DUMP} from backup..."
# Execute pg_dump command with or without --verbose flag based on VERBOSE_MODE
if $VERBOSE_MODE; then
    docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} pg_restore --exit-on-error --no-owner --no-acl --user=seed -d seed -v ${PG12_DUMP}
else
    docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} pg_restore --exit-on-error --no-owner --no-acl --user=seed -d seed ${PG12_DUMP}
fi


echo "Performing post-restore operations for TimescaleDB..."
# Post restore with TimescaleDB
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d seed -c 'SELECT timescaledb_post_restore();'

echo "Verifying the TimescaleDB extension post-restore..."
# Check the extension again
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d seed -c '\dx timescaledb'

echo "Updating TimescaleDB extension to ensure it's at the latest compatible version..."
docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d seed -c 'ALTER EXTENSION timescaledb UPDATE;'

# Capture the PostgreSQL version from the container
POSTGRES_VERSION=$(docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d postgres -t -A -c 'SHOW server_version;' | cut -d ' ' -f1)

# Capture the TimescaleDB version from the container using SQL command
TIMESCALE_VERSION=$(docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} psql --user=seed -d postgres -t -A -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';")
export CONV_DUMP="/share/seed-pg${POSTGRES_VERSION}-${TIMESCALE_VERSION}-$(date +%Y%m%d%H%M%S).dump"
echo "Dumping upgraded Postgres Version: ${POSTGRES_VERSION}, TimescaleDB Version: ${TIMESCALE_VERSION} to file: ${CONV_DUMP}..."
if $VERBOSE_MODE; then
    docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} pg_dump --username=seed --dbname=seed --verbose --no-owner --no-acl -Z7 -Fc -f "${CONV_DUMP}"
else
    docker-compose exec -T ${SOURCE_PG_TIMESCALE_CONV_SERVICE} pg_dump --username=seed --dbname=seed --no-owner --no-acl -Z7 -Fc -f "${CONV_DUMP}"
fi




echo "============================================"
echo "Transitioning to ${PG_TEST_STRING}"
echo "============================================"

echo "Waiting for ${TARGET_PG_TIMESCALE_TEST_SERVICE} to start..."
# Wait until ${PG_TEST-STRING} starts and is ready to accept connections.
until docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} pg_isready -U seed -d seed > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done

echo
echo "${PG_TEST_STRING} is up and running."
echo

echo "Checking initial PostgreSQL and TimescaleDB versions for ${PG_TEST-STRING}..."
# Show PostgreSQL version
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d postgres -c 'SELECT version();'

# Show TimescaleDB version
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d postgres -c '\dx timescaledb'

echo "Setting up database and extensions on ${PG_TEST-STRING}..."

# Now, attempt to drop the 'seed' database
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d postgres -c 'DROP DATABASE IF EXISTS "seed";'

# Create the "seed" database with the owner "seed"
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d postgres -c 'CREATE DATABASE "seed" WITH OWNER = "seed";'

# Grant all privileges on the "seed" database to the user "seed"
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -c 'GRANT ALL PRIVILEGES ON DATABASE "seed" TO "seed";'

# Alter the user "seed" to have CREATEDB, CREATEROLE, and SUPERUSER privileges
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -c 'ALTER USER "seed" CREATEDB CREATEROLE SUPERUSER;'

# Create the PostGIS extension if it does not exist
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d seed -c 'CREATE EXTENSION IF NOT EXISTS postgis;'

# Prepare for restore with TimescaleDB
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d seed -c 'SELECT timescaledb_pre_restore();'

echo "Restoring ${PG_CONV_STRING} database ${CONV_DUMP} from backup..."
# Restore from backup
# Execute pg_dump command with or without --verbose flag based on VERBOSE_MODE
if $VERBOSE_MODE; then
    docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} pg_restore --exit-on-error --no-owner --no-acl --user=seed -d seed -v ${CONV_DUMP}
else
    docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} pg_restore --exit-on-error --no-owner --no-acl --user=seed -d seed ${CONV_DUMP}
fi


# Prepare for restore with TimescaleDB
docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d seed -c 'SELECT timescaledb_post_restore();'

# Capture the PostgreSQL version from the containerP
POSTGRES_VERSION=$(docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d postgres -t -A -c 'SHOW server_version;' | cut -d ' ' -f1)
TIMESCALE_VERSION=$(docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} psql --user=seed -d postgres -t -A -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';")
export TEST_DUMP="/share/seed-pg${POSTGRES_VERSION}-${TIMESCALE_VERSION}-$(date +%Y%m%d%H%M%S).dump"
echo "Dumping upgraded PostgresV: ${POSTGRES_VERSION} TimescaleV: ${TIMESCALE_VERSION} file of $TEST_DUMP..."
if $VERBOSE_MODE; then
    docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} pg_dump --username=seed --dbname=seed --verbose --no-owner --no-acl -Z7 -Fc -f "${TEST_DUMP}"
else
    docker-compose exec -T ${TARGET_PG_TIMESCALE_TEST_SERVICE} pg_dump --username=seed --dbname=seed --no-owner --no-acl -Z7 -Fc -f "${TEST_DUMP}"
fi

export COMPOSE_FILE=docker-compose.pgupgrade.yml
docker-compose stop ${SOURCE_PG_TIMESCALE_CONV_SERVICE}
docker-compose stop ${TARGET_PG_TIMESCALE_TEST_SERVICE}
unset COMPOSE_FILE
echo "Database operations completed."
