#!/bin/bash -x

IMAGETAG=skip
if [ "${TRAVIS_BRANCH}" == "develop" ]; then
    IMAGETAG=develop
elif [ "${TRAVIS_BRANCH}" == "master" ]; then
    # Retrieve the version number from package.json
    IMAGETAG=$( sed -n 's/.*"version": "\(.*\)",/\1/p' package.json )
fi

if [ "${IMAGETAG}" != "skip" ] && [ "${TRAVIS_PULL_REQUEST}" == "false" ]; then
    docker-compose build --pull
    docker login -u $DOCKER_USER -p $DOCKER_PASS

    echo "Tagging image as $IMAGETAG"
    docker tag seedplatform/seed seedplatform/seed:$IMAGETAG
    docker push seedplatform/seed:$IMAGETAG
else
    echo "Not on a deployable branch this is a pull request"
fi
