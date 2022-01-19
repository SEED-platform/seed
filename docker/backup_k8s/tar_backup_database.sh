#!/bin/bash

# This back up script grabs the lastest pg_dump, restores it, tars it, and
# uploads it when SEED is running in a docker container. This is to be used
# in conjunction with k8s and a CronJob task.

DB_USERNAME=$1

send_slack_notification(){
    if [ ! -z ${APP_SLACK_WEBHOOK} ]; then
        payload='payload={"text": "'$1'"}'
        cmd1= curl --silent --data-urlencode "$(printf "%s" $payload)" ${APP_SLACK_WEBHOOK} || true
    else
        echo "No APP_SLACK_WEBHOOK"
    fi
}

# Verify that the following required enviroment variables are set
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

if [ -z ${PGPASSWORD} ]; then
    echo "PGPASSWORD is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-PGPASSWORD-not-configured"
    exit 1
fi

# Instal aws cli
apk add --no-cache \
    python3 \
    py3-pip \
&& pip3 install --upgrade pip \
&& pip3 install awscli

LATEST_DIR="$(aws s3 ls seed-dev1-backups | sort | tail -n 1 | awk -F' ' '{print $2}')"

# if backup.tar already exists, for go rest of script
if aws s3 ls  $S3_BUCKET/$LATEST_DIR | grep "backup.tar"; then
    echo "There's already a backup for $LATEST_DIR"; 
    exit 0

fi

# work in the scratch volume for storage
cd /scratch

# Download latest S3 backup
aws s3 cp $S3_BUCKET/$LATEST_DIR . --recursive --exclude "*" --include "*.dump"

# Start postgres
su postgres -c "initdb"
su postgres -c "pg_ctl start"

# Restore db 
su postgres -c "createuser ${DB_USERNAME}"
su postgres -c "pg_restore -v -C -d postgres ./seed*.dump"

# Stop postgres
su postgres -c "pg_ctl stop"

# tar db
tar -czf backup.tar /var/lib/postgresql/data

# push tared db to s3
aws s3 cp backup.tar $S3_BUCKET/$LATEST_DIR
