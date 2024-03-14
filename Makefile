BASE_IMAGE_TAG = 3.9

ifdef AWS_ACCOUNT_ID
  REGISTRY-IDS=$(AWS_ACCOUNT_ID)
else
  $(error AWS_ACCOUNT_ID is not set)
endif

REPO = $(REGISTRY-IDS).dkr.ecr.us-west-2.amazonaws.com/$(IMAGE_REPO_NAME)

ifdef RELEASE_SHA2
  HEAD_VER=$(RELEASE_SHA2)
else ifdef RELEASE_SHA1
  HEAD_VER=$(RELEASE_SHA1)
else
	HEAD_VER=$(shell git log -1 --pretty=tformat:%h)
endif

$(info HEAD_VER="$(HEAD_VER)")

ifdef BRANCH_NAME2
	BRANCH_NAME=$(BRANCH_NAME2)
else ifdef BRANCH_NAME1
	BRANCH_NAME=$(BRANCH_NAME1)
else
	BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
endif

# Normalize branch name for Docker tag compatibility
BRANCH_NAME_SAFE = $(subst /,-,$(BRANCH_NAME))

$(info BRANCH_NAME_SAFE="$(BRANCH_NAME_SAFE)")

# git release version - use for rollbacks
TAG ?= $(BASE_IMAGE_TAG)-$(BRANCH_NAME_SAFE)-$(HEAD_VER)

.PHONY: build push

build:
	docker build -t $(REPO):$(TAG) \
	  -f Dockerfile \
      --build-arg NGINX_LISTEN_OPTS=$(NGINX_LISTEN_OPTS) \
		./

push:
	docker push $(REPO):$(TAG)
