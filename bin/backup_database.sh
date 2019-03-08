#!/bin/bash

# Nightly backups - crontab
# 0 0 * * * /home/ubuntu/prj/seed/bin/backup_database.sh <db_name> <db_username> <db_password> <media_dir> >> /home/ubuntu/seed-backups/cron.log 2>&1

DB_NAME=$1
DB_USERNAME=$2
# Set PGPASSWORD as pg_dump uses this env var.
DB_PASSWORD=$3
MEDIA_DIR=$4

function file_name(){
    echo ${BACKUP_DIR}/${DB_NAME}_$(date '+%Y%m%d_%H%M%S').dump
}

function media_file_name(){
    echo ${BACKUP_DIR}/${DB_NAME}_media_$(date '+%Y%m%d_%H%M%S').tgz
}

if [[ (-z ${DB_NAME}) || (-z ${DB_USERNAME}) || (-z ${DB_PASSWORD}) ]] ; then
    echo "Expecting command to be of form ./backup_database.sh <db_name> <db_username> <db_password>"
    exit 1
fi

# currently the backup directory is hard coded
BACKUP_DIR=~/seed-backups
mkdir -p ${BACKUP_DIR}

export PGPASSWORD=${DB_PASSWORD}
echo "pg_dump -U ${DB_USERNAME} -Fc ${DB_NAME} > $(file_name)"
pg_dump -U ${DB_USERNAME} -Fc ${DB_NAME} > $(file_name)
unset PGPASSWORD

# Backup the media directory (uploads, especially buildingsync)
if [[ (! -z ${MEDIA_DIR}) ]] ; then
  tar zcvf $(media_file_name) ${MEDIA_DIR}
fi

# Delete files older than 45 days
find ${BACKUP_DIR} -mtime +45 -type f -name '*.dump' -delete
find ${BACKUP_DIR} -mtime +45 -type f -name '*.tgz' -delete

