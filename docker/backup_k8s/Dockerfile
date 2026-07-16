# Author: Nicholas Long
#
# This docker container is used to create a backup of the seed database and
# mediafiles, then push the backups to S3. The script itself is the backup_database.sh
# script that is copied into this container for use by helm/k8s batch/CronJob.

# docker build -f docker/backup_k8s/Dockerfile -t seedplatform/seed-backup-k8s .
# tag this as needed, latest is automatically pulled by helm at the moment.
# docker tag seedplatform/seed-backup-k8s:latest seedplatform/seed-backup-k8s:{tag}
# docker push seedplatform/seed-backup-k8s:{tag}

FROM ubuntu:26.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Keys to access the s3 backups
ENV AWS_ACCESS_KEY_ID ""
ENV AWS_SECRET_ACCESS_KEY ""
ENV AWS_DEFAULT_REGION ""
ENV S3_BUCKET_NAME ""

# Run the update and install the PostgreSQL client used for pg_dump.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        awscli \
        ca-certificates \
        curl \
        gnupg && \
    install -d /usr/share/postgresql-common/pgdg && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /tmp/postgresql.asc && \
    gpg --dearmor -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg /tmp/postgresql.asc && \
    rm /tmp/postgresql.asc && \
    . /etc/os-release && \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] http://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client-18 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
ADD backup_database.sh /app/
