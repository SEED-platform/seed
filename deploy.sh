#!/bin/bash -e

# This script requires several environmental variables to be set to deploy. Note that if the
# users already exist in SEED or Postgres then they will not be recreated and their passwords
# will not be updated.

# Version 2020-04-03: Convert to using docker-compose. Docker stack/swarm was causing issues with DNS resolution
#                     within the container. If you are currently using docker swarm, then remove your stack
#                     `docker stack rm seed` and then redeploy with this script.

: << 'arguments'
There is only one optional argument and that is the name of the docker compose file to load.
For example: ./deploy.sh docker-compose.local.oep.yml

There are several required environment variables that need to be set in order to launch seed:
POSTGRES_DB (required), name of the POSTGRES DB
DJANGO_SETTINGS_MODULE (optional), defaults to config.settings.docker
POSTGRES_USER (required), admin user of postgres database
POSTGRES_PASSWORD (required), admin password for postgres database
SEED_ADMIN_USER (required), admin user for SEED
SEED_ADMIN_PASSWORD (required), admin password for SEED
SEED_ADMIN_ORG (required), default organization for admin user in SEED
SECRET_KEY (required), unique key for SEED web application
AWS_ACCESS_KEY_ID (optional), Access key for AWS
AWS_SECRET_ACCESS_KEY, Secret key for AWS
AWS_SES_REGION_NAME (optional), AWS Region for SES
AWS_SES_REGION_ENDPOINT (optional), AWS endpoint for SES
SERVER_EMAIL (optional), Email that is used by the server to send messages
SENTRY_JS_DSN (optional), Sentry JavaScript DSN
SENTRY_RAVEN_DSN (optional), Sentry Django DSN (Raven-based)

# example (do not use these values in production).
export POSTGRES_USER=seeduser
export POSTGRES_PASSWORD=super-secret-password
export SEED_ADMIN_USER=user@seed-platform.org
export SEED_ADMIN_PASSWORD=super-secret-password
export SEED_ADMIN_ORG=default
export SECRET_KEY=ARQV8qGuJKH8sGnBf6ZeEdJQRKLTUhsvEcp8qG9X9sCPXvGLhdxqnNXpZcy6HEyf
# If using SES for email, then you need to also pass in the following optional arguments (change as
# needed):
export AWS_ACCESS_KEY_ID=key
export AWS_SECRET_ACCESS_KEY=secret_key
export AWS_SES_REGION_NAME=us-west-2
export AWS_SES_REGION_ENDPOINT=email.us-west-2.amazonaws.com
export SERVER_EMAIL=info@seed-platform.org
export SENTRY_JS_DSN=https://bcde@sentry.io/123456789
export SENTRY_RAVEN_DSN=https://abcd:1234@sentry.io/123456789
arguments

# Verify that env vars are set
if [ -z ${POSTGRES_DB+x} ]; then
    echo "POSTGRES_DB is not set"
    exit 1
fi

if [ -z ${POSTGRES_USER+x} ]; then
    echo "POSTGRES_USER is not set"
    exit 1
fi

if [ -z ${POSTGRES_PASSWORD+x} ]; then
    echo "POSTGRES_PASSWORD is not set"
    exit 1
fi

if [ -z ${SEED_ADMIN_USER+x} ]; then
    echo "SEED_ADMIN_USER is not set"
    exit 1
fi

if [ -z ${SEED_ADMIN_USER+x} ]; then
    echo "SEED_ADMIN_USER is not set"
    exit 1
fi

if [ -z ${SEED_ADMIN_PASSWORD+x} ]; then
    echo "SEED_ADMIN_PASSWORD is not set"
    exit 1
fi

if [ -z ${SEED_ADMIN_ORG+x} ]; then
    echo "SEED_ADMIN_PASSWORD is not set"
    exit 1
fi

if [ -z ${SECRET_KEY+x} ]; then
    echo "SECRET_KEY is not set"
    exit 1
fi

DOCKER_COMPOSE_FILE=docker-compose.local.yml
if [ -z "$1" ]; then
    echo "There are no arguments, defaulting to use '${DOCKER_COMPOSE_FILE}'."
else
    DOCKER_COMPOSE_FILE=$1
    echo "Using passed docker-compose file of ${DOCKER_COMPOSE_FILE}"
fi

# Swarm is needed for the registry
if docker node ls > /dev/null 2>&1; then
  echo "Swarm already initialized"
else
  docker swarm init
fi

if docker exec $(docker ps -qf "name=registry") true > /dev/null 2>&1; then
    echo "Registry is already running"
else
    echo "Creating registry"
    docker volume create --name=regdata
    docker service create --name registry --publish 5000:5000 --mount type=volume,source=regdata,destination=/var/lib/registry registry:2.6
fi

echo "Building latest version of SEED with OEP option"
# explicitly pull images from docker-compose's build yml file. Note that you will need to keep the
# versions consistent between the compose file and what is below.
docker-compose -f docker-compose.build.yml pull
docker-compose -f docker-compose.build.yml build --pull

# Get the versions out of the docker-compose.build file
DOCKER_PG_VERSION=$( sed -n 's/.*image\: timescale\/timescaledb-postgis\:latest-pg\(.*\)/\1/p' docker-compose.build.yml )
DOCKER_OEP_VERSION=$( sed -n 's/.*image\: seedplatform\/oep\:\(.*\)/\1/p' docker-compose.build.yml )
DOCKER_REDIS_VERSION=$( sed -n 's/.*image\: redis\:\(.*\)/\1/p' docker-compose.build.yml )

echo "Tagging local containers"
docker tag seedplatform/seed:latest 127.0.0.1:5000/seed
docker tag timescale/timescaledb-postgis:latest-pg$DOCKER_PG_VERSION 127.0.0.1:5000/postgres-seed
docker tag redis:5.0.1 127.0.0.1:5000/redis
docker tag seedplatform/oep:$DOCKER_OEP_VERSION 127.0.0.1:5000/oep

sleep 3
echo "Pushing tagged versions to local registry"
docker push 127.0.0.1:5000/seed
docker push 127.0.0.1:5000/postgres-seed
docker push 127.0.0.1:5000/redis
docker push 127.0.0.1:5000/oep

echo "Deploying (or updating)"
docker-compose -f ${DOCKER_COMPOSE_FILE} -p seed up -d
wait $!
while ( nc -zv 127.0.0.1 80 3>&1 1>&2- 2>&3- ) | awk -F ":" '$3 != " Connection refused" {exit 1}'; do echo -n "."; sleep 5; done
echo "SEED stack redeployed"

echo "Waiting for webserver to respond"
until curl -sf --output /dev/null "127.0.0.1"; do echo -n "."; sleep 1; done
