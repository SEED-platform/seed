#!/bin/bash -x

docker-compose build --pull
docker login -e $DOCKER_EMAIL -u $DOCKER_USER -p $DOCKER_PASS
docker push seedplatform/seed
