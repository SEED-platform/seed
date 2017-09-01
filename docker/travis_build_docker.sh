#!/bin/bash -x

export IMAGETAG=initial-version
echo $IMAGETAG
docker-compose build --pull
# docker login -e $DOCKER_EMAIL -u $DOCKER_USER -p $DOCKER_PASS
docker tag seedplatform/seed seedplatform/seed:$IMAGETAG
docker push seedplatform/seed:$IMAGETAG
