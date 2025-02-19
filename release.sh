#!/bin/bash
set -euo pipefail

# Variables
export PROJECT_HANDLE=seedcerl
export APP_NAME=seedweb

export MAKEFILE_PATH=./appfleet-config/Makefile
export APPFLEET_RELEASE_NAME=dev
export APPFLEET_DEPLOY_VERSION=2.2.1-alpine-e1f2893
export BASE_IMAGE_TAG=3.9
# Properly format the JSON for APPFLEET_BUILD_ARGS
export APPFLEET_BUILD_ARGS='{"main": {"image_detail": "./appfleet-config/mainDetail.json", "dockerfile": "./Dockerfile.ecs", "ecr_repo": "$(REGISTRY-IDS).dkr.ecr.us-west-2.amazonaws.com/nrel-seedcerl-seedweb", "target_arg": ""}}'
export APPFLEET_DOCKER_BUILD_ARGS='{"BASE_IMAGE_TAG": "3.9", "NGINX_LISTEN_OPTS": "$(NGINX_LISTEN_OPTS)"}'
export CACHE_S3_BUCKET=nrel-seedcerl-seedweb-codebuild

# Optional: log in to ECR if necessary
# aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 991404956194.dkr.ecr.us-west-2.amazonaws.com

echo "Setting up docker buildx builder..."
if docker buildx inspect mybuilder > /dev/null 2>&1; then
    echo "Builder 'mybuilder' already exists. Using it."
    docker buildx use mybuilder
else
    docker buildx create --use --name mybuilder --driver docker-container
fi

echo "Running make buildx..."
# Run the build command and exit immediately if it fails.
make -f "$MAKEFILE_PATH" V=1 buildx

echo "Running generate_appfleet_tag_overrides.sh to populate APPFLEET_TAG_OVERRIDES..."
APPFLEET_TAG_OVERRIDES=$(./appfleet-config/generate_appfleet_tag_overrides.sh)
echo "APPFLEET_TAG_OVERRIDES: $APPFLEET_TAG_OVERRIDES"

echo "Running make deploy..."
make -f "$MAKEFILE_PATH" V=1 APPFLEET_TAG_OVERRIDES="$APPFLEET_TAG_OVERRIDES" deploy
