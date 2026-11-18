# Author: Nicholas Long
#
# This docker container is used to create a backup of the seed database and
# mediafiles, then push the backups to S3. The script itself is the backup_database.sh
# script that is copied into this container for use by helm/k8s batch/CronJob.

# Build with this directory as the context, and push the tag the helm CronJobs pull
# (pg18, matching the PostgreSQL client installed below). From the repository root:
# docker build -t seedplatform/seed-backup-k8s:pg18 docker/backup_k8s
# docker push seedplatform/seed-backup-k8s:pg18

FROM ubuntu:26.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# backup_database.sh reads AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION,
# S3_BUCKET, and PGPASSWORD (plus optional ENVIRONMENT and APP_SLACK_WEBHOOK) at run time

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
