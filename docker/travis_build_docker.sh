#!/bin/bash -x

if [ "$TRAVIS_BRANCH" == "develop" ]; then
    IMAGETAG=develop
elif [ "$TRAVIS_BRANCH" == "bricr" ]; then
    IMAGETAG=bricr
elif [ "$TRAVIS_BRANCH" == "master" ]; then
    # Retrieve the version number from package.json
    IMAGETAG=$( sed -n 's/.*"version": "\(.*\)",/\1/p' package.json )
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
