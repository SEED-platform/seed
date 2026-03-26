# Author: Nicholas Long
#
# This docker container is used to create a backup of the seed database and
# mediafiles, then push the backups to S3. The script itself is the backup_database.sh
# script that is copied into this container for use by helm/k8s batch/CronJob.

# docker build -f docker/backup_k8s/Dockerfile -t seedplatform/seed-backup-k8s .
# tag this as needed, latest is automatically pulled by helm at the moment.
# docker tag seedplatform/seed-backup-k8s:latest seedplatform/seed-backup-k8s:{tag}
# docker push seedplatform/seed-backup-k8s:{tag}

FROM ubuntu:20.04
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Keys to access the s3 backups
ENV AWS_ACCESS_KEY_ID ""
ENV AWS_SECRET_ACCESS_KEY ""
ENV AWS_DEFAULT_REGION ""
ENV S3_BUCKET_NAME ""
ENV UV_PYTHON_INSTALL_DIR="/opt/uv/python"
ENV UV_TOOL_BIN_DIR="/usr/local/bin"
ENV UV_TOOL_DIR="/opt/uv-tools"

WORKDIR /uv-bootstrap
COPY ./.python-version /uv-bootstrap/.python-version

# Run the Update and install k8s key
RUN apt update && \
    apt upgrade -y && \
    apt install -y \
        curl \
        apt-transport-https \
        ca-certificates \
        gnupg && \
    uv tool install --managed-python awscli && \
    # install postgres client for pg_dump for backup - SEED is currently on pg12
    # This is hardcoded with the ubuntu 20 (focal) release.
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt focal-pgdg main" > /etc/apt/sources.list.d/pgdg.list' && \
    apt update && \
    apt install -y postgresql-client-12

WORKDIR /app
ADD backup_database.sh /app/
