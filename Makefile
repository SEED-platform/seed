BASE_IMAGE_TAG = 3.9

PROJECT_NAME=nrel179d-seedweb


ifdef ACCOUNT_ID
  REGISTRY-IDS=$(ACCOUNT_ID)
else ifdef AWS_ACCOUNT_ID
  REGISTRY-IDS=$(AWS_ACCOUNT_ID)
else
  $(error ACCOUNT_ID is not set)
endif

REPO = $(REGISTRY-IDS).dkr.ecr.us-west-2.amazonaws.com/nrel-$(PROJECT_NAME)

ifdef RELEASE_SHA
  HEAD_VER=$(RELEASE_SHA)
else ifdef CODEBUILD_SOURCE_VERSION
  HEAD_VER=$(CODEBUILD_SOURCE_VERSION)
else
	HEAD_VER=$(shell git log -1 --pretty=tformat:%h)
endif

$(info HEAD_VER="$(HEAD_VER)")
ifdef BRANCH_NAME
  RELEASE_TAG ?= $(BRANCH_NAME)-$(HEAD_VER)
else ifdef CODEBUILD_WEBHOOK_HEAD_REF
  RELEASE_TAG ?= $(CODEBUILD_WEBHOOK_HEAD_REF)-$(HEAD_VER)
else
	RELEASE_TAG = $(HEAD_VER)
endif

$(info RELEASE_TAG="$(RELEASE_TAG)")
# git release version - use for rollbacks
#3.9-dev VS 3.9-a51016d
TAG ?= $(BASE_IMAGE_TAG)-$(RELEASE_TAG)

.PHONY: build push

build:
	docker build -t $(REPO):$(TAG) \
	  -f Dockerfile \
		./

push:
	docker push $(REPO):$(TAG)
