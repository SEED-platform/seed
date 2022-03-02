#!/bin/bash

# This back up script grabs the latest pg_dump, restores it, tars it, and
# uploads it when SEED is running in a docker container. This is to be used
# in conjunction with k8s and a CronJob task, and runs as the `postgres` user.

send_slack_notification(){
    if [ ! -z ${APP_SLACK_WEBHOOK} ]; then
        payload='payload={"text": "'$1'"}'
        cmd1= curl --silent --data-urlencode "$(printf "%s" $payload)" ${APP_SLACK_WEBHOOK} || true
    else
        echo "No APP_SLACK_WEBHOOK"
    fi
}

# Verify that the following required environment variables are set
if [ -z ${AWS_ACCESS_KEY_ID} ]; then
    echo "AWS_ACCESS_KEY_ID is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-AWS_ACCESS_KEY_ID-not-configured"
    exit 1
fi

if [ -z ${AWS_SECRET_ACCESS_KEY} ]; then
    echo "AWS_SECRET_ACCESS_KEY is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-AWS_SECRET_ACCESS_KEY-not-configured"
    exit 1
fi

if [ -z ${AWS_DEFAULT_REGION} ]; then
    echo "AWS_DEFAULT_REGION is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-AWS_DEFAULT_REGION-not-configured"
    exit 1
fi

if [ -z ${S3_BUCKET} ]; then
    echo "S3_BUCKET is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-S3_BUCKET-not-configured"
    exit 1
fi

if [ -z ${POSTGRES_DB} ]; then
    echo "POSTGRES_DB is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-POSTGRES_DB-not-configured"
    exit 1
fi

if [ -z ${POSTGRES_USER} ]; then
    echo "POSTGRES_USER is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-POSTGRES_USER-not-configured"
    exit 1
fi

if [ -z ${POSTGRES_PASSWORD} ]; then
    echo "POSTGRES_PASSWORD is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-POSTGRES_PASSWORD-not-configured"
    exit 1
fi

LATEST_DIR="$(aws s3 ls seed-dev1-backups | sort | tail -n 1 | awk -F' ' '{print $2}')"
ARCHIVE=backup.tar.xz

# if backup already exists, forgo rest of script
if aws s3 ls $S3_BUCKET/$LATEST_DIR | grep $ARCHIVE; then
    echo "There's already a backup for $LATEST_DIR";
    send_slack_notification "[ERROR-$ENVIRONMENT]-backup-already-exists-for-$LATEST_DIR"
    exit 0
fi

# work in the scratch volume for storage
cd /scratch
# make sure that the scratch volume does not have
# any preexisting dumps as it will crash the pg_restore
# command below.
rm -f seed*.dump

# Download latest S3 backup
aws s3 cp $S3_BUCKET/$LATEST_DIR . --recursive --exclude "*" --include "seed*.dump"

# Restart for timescale-tune to take effect
pg_ctl restart

# Restore db
psql -U $POSTGRES_USER $POSTGRES_DB -c 'SELECT timescaledb_pre_restore();'
pg_restore -U $POSTGRES_USER -d $POSTGRES_DB ./seed*.dump
psql -U $POSTGRES_USER $POSTGRES_DB -c 'SELECT timescaledb_post_restore();'

# Stop postgres
pg_ctl stop

# compress pgdata
tar -cJf $ARCHIVE /var/lib/postgresql/data

# push archived db to s3
aws s3 cp $ARCHIVE $S3_BUCKET/$LATEST_DIR

send_slack_notification "[$ENVIRONMENT]-tar-db-backup-uploaded-to-$S3_BUCKET/$LATEST_DIR/$ARCHIVE"

exit 0
