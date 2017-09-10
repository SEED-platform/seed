#!/bin/bash -x

if [ "$TRAVIS_BRANCH" == "develop" ]; then
    IMAGETAG=develop
elif [ "$TRAVIS_BRANCH" == "bricr" ]; then
    IMAGETAG=bricr
fi

docker-compose build --pull
docker login -u $DOCKER_USER -p $DOCKER_PASS

if [ -n "$IMAGETAG" ]; then
    echo "Tagging image as $IMAGETAG"
    docker tag seedplatform/seed seedplatform/seed:$IMAGETAG
    docker push seedplatform/seed:$IMAGETAG
else
    echo "No tag found, skipping"
fi
