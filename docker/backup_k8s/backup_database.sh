#!/bin/bash

# This backup script creates nightly database and media file backups of SEED when SEED is running
# in a docker container. This is to be used in conjunction with k8s and
# a CronJob task.

DB_HOST=$1
DB_NAME=$2
DB_USERNAME=$3

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

if [ -z ${PGPASSWORD} ]; then
    echo "PGPASSWORD is not set"
    send_slack_notification "[ERROR-$ENVIRONMENT]-PGPASSWORD-not-configured"
    exit 1
fi

# currently the backup directory is hard coded
BACKUP_DIR=/app/backups
mkdir -p ${BACKUP_DIR}

# get the run date to save as the s3 folder name
RUN_DATE=$(date +%Y-%m-%d)

function file_name(){
    echo ${BACKUP_DIR}/${DB_NAME}_$(date '+%Y%m%d_%H%M%S').dump
}

function media_file_name(){
    echo ${BACKUP_DIR}/${DB_NAME}_media_$(date '+%Y%m%d_%H%M%S').tgz
}

if [[ (-z ${DB_NAME}) || (-z ${DB_USERNAME}) ]] ; then
    echo "Expecting command to be of form ./backup_database.sh <POD> <db_name> <db_username>"
    exit 1
fi

# db_password is set from the environment variables in docker-compose. The docker stack must
# be running for this command to work.
# echo "docker exec $(docker ps -f "name=db-postgres" --format "{{.ID}}") pg_dump -U ${DB_USERNAME} -Fc ${DB_NAME} > $(file_name)"
echo "Backup up SEED database using pg_dump"
echo "Running: pg_dump -h ${DB_HOST} -U ${DB_USERNAME} -Fc ${DB_NAME} > $(file_name)"
pg_dump -h ${DB_HOST} -U ${DB_USERNAME} -Fc ${DB_NAME} > $(file_name)

# Backup the media directory (uploads, especially buildingsync). In docker-land this is
# just a container volume which needs to been mapped to this pod in the k8s CronJob.
echo "Backing up media data"
tar zcvf $(media_file_name) /mediadata

# Delete files older than 30 days that are on disk (which should be none because it is a new pod)
find ${BACKUP_DIR} -mtime +30 -type f -name '*.dump' -delete
find ${BACKUP_DIR} -mtime +30 -type f -name '*.tgz' -delete

# upload to s3
for file in $BACKUP_DIR/*.dump
do
  echo "Backing up $file to $S3_BUCKET/$RUN_DATE/"
  if [ ! -s $file ]; then
    # the file is empty, send an error
    send_slack_notification "[ERROR-$ENVIRONMENT]-PostgreSQL-backup-file-was-empty-or-missing"
  else
    # can't pass spaces to slack notifications, for now
    aws s3 cp $file $S3_BUCKET/$RUN_DATE/
    send_slack_notification "[$ENVIRONMENT]-PostgreSQL-uploaded-to-$S3_BUCKET/$RUN_DATE/$(basename $file)"
  fi
done

for file in $BACKUP_DIR/*.tgz
do
  echo "Backing up $file $S3_BUCKET/$RUN_DATE/"

  if [ ! -s $file ]; then
    # the file is empty, send an error
    send_slack_notification "[ERROR-$ENVIRONMENT]-Mediadata-backup-file-was-empty-or-missing"
  else
    # can't pass spaces to slack notifications, for now
    aws s3 cp $file $S3_BUCKET/$RUN_DATE/
    send_slack_notification "[$ENVIRONMENT]-Mediadata-uploaded-to-$S3_BUCKET/$RUN_DATE/$(basename $file)"
  fi
done

send_slack_notification "[$ENVIRONMENT]-database-backup-run-completed"

# The section below to the end is to clean out old S3 backups.
# In general, keep
#  - Last 90 nightly backups
#  - Last 52 weeks of Monday morning backups
#  - Last 10 years of monthly data

# Daily - add dates in format "2021-10-22" to the keep array.
for i in {0..60}
do
    ((keep[$(date +%Y%m%d -d "-$i day")]++))
done

# Last 52 weeks of Monday morning backups. "monday-i week" is method to get previous monday back i times.
for i in {0..52}
do
    vali=$((i+1))
    ((keep[$(date "+%Y%m%d" -d "monday-$vali week")]++))
done

# Last 10 years of monthly data on a monday. This is the most confusing, need to first grab the 15th of each month back 120 times.
# Then find the number of weeks back was the monday for the month of interest, then add that to the keep array.
for i in {0..120}; do
    DW=$(($(date +%-W)-$(date -d $(date -d "$(date +%Y-%m-15) -$i month" +%Y-%m-01) +%-W)))
    for (( AY=$(date -d "$(date +%Y-%m-15) -$i month" +%Y); AY < $(date +%Y); AY++ )); do
        ((DW+=$(date -d $AY-12-31 +%W)))
    done
    ((keep[$(date +%Y%m%d -d "monday-$DW weeks")]++))
done

# Query S3 to find all the dates that exist. Mapfile converts output or CRLF stdout to array in bash.
mapfile s3dirs < <(aws s3 ls $S3_BUCKET | awk '{print $2}')

# Iterate to find which backups need to be removed
for s3dir in "${s3dirs[@]}"
do
    date_found=false
    for keepvalue in "${!keep[@]}"
    do
        val=${keepvalue:0:4}-${keepvalue:4:2}-${keepvalue:6:2}
        if [ "${s3dir:0:10}" == "$val" ] ; then
            echo "Found Backup, skipping"
            date_found=true
        fi
    done

    # This method can be quite destructive and delete any
    # files that are in the date format. Be sure to
    # test this script before deploying in any production
    # environment. It will only remove directories that
    # have a YYYY-MM-DD format
    if [ "$date_found" = false ] && [[ "${s3dir:0:10}" =~ ^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$ ]]; then
        echo "Deleting out of date backup of ${s3dir:0:10}"
        aws s3 rm $S3_BUCKET/${s3dir:0:10} --recursive
    fi
done
