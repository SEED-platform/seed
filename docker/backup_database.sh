#!/bin/bash

# This backup script creates nightly database and media file backups of SEED when SEED is running
# in a docker container.

# To create nightly backups, add the following to your crontab
# 0 0 * * * /home/ubuntu/prj/seed/docker/backup_database.sh <docker-compose-filename> <db_name> <db_username>

DC_FILENAME=$1
DB_NAME=$2
DB_USERNAME=$3

function file_name(){
    echo ${BACKUP_DIR}/${DB_NAME}_$(date '+%Y%m%d_%H%M%S').dump
}

function media_file_name(){
    echo /backup/dir/${DB_NAME}_media_$(date '+%Y%m%d_%H%M%S').tgz
}

if [[ (-z ${DB_NAME}) || (-z ${DB_USERNAME}) || (-z ${DC_FILENAME}) ]] ; then
    echo "Expecting command to be of form ./backup_database.sh <docker-compose-filename> <db_name> <db_username>"
    exit 1
fi

# currently the backup directory is hard coded
BACKUP_DIR=~/seed-backups
mkdir -p ${BACKUP_DIR}

# db_password is set from the environment variables in docker-compose. The docker stack must
# be running for this command to work.
echo "docker-compose -f ${DC_FILENAME} exec $(docker ps -f "name=db-postgres" --format "{{.ID}}") pg_dump -U ${DB_USERNAME} -Fc ${DB_NAME} > $(file_name)"
docker-compose -f ${DC_FILENAME} exec $(docker ps -f "name=db-postgres" --format "{{.ID}}") pg_dump -U ${DB_USERNAME} -Fc ${DB_NAME} > $(file_name)

# Backup the media directory (uploads, especially buildingsync). In docker-land this is
# just a container volume, so create a new container with the volume attached and tar it up.
echo "docker run --rm -it -v seed_media:/backup/media -v $BACKUP_DIR:/backup/dir/ alpine:3.8 tar zcvf $(media_file_name) /backup/media"
docker run --rm -it -v seed_media:/backup/media -v $BACKUP_DIR:/backup/dir/ alpine:3.8 tar zcvf $(media_file_name) /backup/media

# Delete files older than 45 days.
find ${BACKUP_DIR} -mtime +45 -type f -name '*.dump' -delete
find ${BACKUP_DIR} -mtime +45 -type f -name '*.tgz' -delete
