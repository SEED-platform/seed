#!/bin/bash

set -euo pipefail

# This back up script grabs the latest pg_dump, restores it, tars it, and
# uploads it when SEED is running in a docker container. This is to be used
# in conjunction with k8s and a CronJob task, and runs as the `postgres` user.

ENVIRONMENT="${ENVIRONMENT:-unknown}"

send_slack_notification(){
    local message="${1:-}"
    local payload

    if [ -n "${APP_SLACK_WEBHOOK:-}" ]; then
        payload="$(printf 'payload={"text": "%s"}' "$message")"
        curl --silent --data-urlencode "$payload" "${APP_SLACK_WEBHOOK}" || true
    else
        echo "No APP_SLACK_WEBHOOK"
    fi
}

# Verify that the following required environment variables are set
if [ -z "${AWS_ACCESS_KEY_ID:-}" ]; then
    echo "AWS_ACCESS_KEY_ID is not set"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-AWS_ACCESS_KEY_ID-not-configured"
    exit 1
fi

if [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    echo "AWS_SECRET_ACCESS_KEY is not set"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-AWS_SECRET_ACCESS_KEY-not-configured"
    exit 1
fi

if [ -z "${AWS_DEFAULT_REGION:-}" ]; then
    echo "AWS_DEFAULT_REGION is not set"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-AWS_DEFAULT_REGION-not-configured"
    exit 1
fi

if [ -z "${S3_BUCKET:-}" ]; then
    echo "S3_BUCKET is not set"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-S3_BUCKET-not-configured"
    exit 1
fi

if [ -z "${POSTGRES_DB:-}" ]; then
    echo "POSTGRES_DB is not set"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-POSTGRES_DB-not-configured"
    exit 1
fi

if [ -z "${POSTGRES_USER:-}" ]; then
    echo "POSTGRES_USER is not set"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-POSTGRES_USER-not-configured"
    exit 1
fi

if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    echo "POSTGRES_PASSWORD is not set"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-POSTGRES_PASSWORD-not-configured"
    exit 1
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"

LATEST_DIR="$(aws s3 ls "$S3_BUCKET" | sort | tail -n 1 | awk -F' ' '{print $2}')"
ARCHIVE=backup.tar.xz

if [ -z "$LATEST_DIR" ]; then
    echo "No backup directories found in $S3_BUCKET"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-no-backup-directories-found"
    exit 1
fi

# if backup already exists, forgo rest of script
if aws s3 ls "$S3_BUCKET/$LATEST_DIR$ARCHIVE" >/dev/null 2>&1; then
    echo "There's already a backup for $LATEST_DIR";
    send_slack_notification "[ERROR-${ENVIRONMENT}]-backup-already-exists-for-$LATEST_DIR"
    exit 0
fi

# work in the scratch volume for storage
cd /scratch
# make sure that the scratch volume does not have
# any preexisting dumps as it will crash the pg_restore
# command below.
rm -f seed*.dump

# Download latest S3 backup
aws s3 cp "$S3_BUCKET/$LATEST_DIR" . --recursive --exclude "*" --include "seed*.dump"

mapfile -t DUMPS < <(find . -maxdepth 1 -type f -name 'seed*.dump' | sort)
if [ "${#DUMPS[@]}" -ne 1 ]; then
    echo "Expected exactly one seed dump in $S3_BUCKET/$LATEST_DIR, found ${#DUMPS[@]}"
    send_slack_notification "[ERROR-${ENVIRONMENT}]-unexpected-seed-dump-count-${#DUMPS[@]}"
    exit 1
fi

# Restart for timescale-tune to take effect
pg_ctl restart

# Restore db
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB" -c 'SELECT timescaledb_pre_restore();'
pg_restore --exit-on-error -U "$POSTGRES_USER" -d "$POSTGRES_DB" "${DUMPS[0]}"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB" -c 'SELECT timescaledb_post_restore();'

# Stop postgres
pg_ctl stop

# compress pgdata
tar -cJf "$ARCHIVE" /home/postgres/pgdata/data

# push archived db to s3
aws s3 cp "$ARCHIVE" "$S3_BUCKET/$LATEST_DIR"

send_slack_notification "[${ENVIRONMENT}]-tar-db-backup-uploaded-to-$S3_BUCKET/$LATEST_DIR/$ARCHIVE"

exit 0
