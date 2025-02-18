-include env_make

# Required environment variables check
REQUIRED_VARS := APPFLEET_DOCKER_BUILD_ARGS PROJECT_HANDLE APP_NAME MAKEFILE_PATH APPFLEET_RELEASE_NAME APPFLEET_DEPLOY_VERSION BASE_IMAGE_TAG CACHE_S3_BUCKET
$(foreach var,$(REQUIRED_VARS),$(if $(value $(var)),,$(error Environment variable $(var) is not set)))

# Environment variables (can be overridden by command-line arguments)
PROJECT_NAME = $(PROJECT_HANDLE)-$(APP_NAME)
APPFLEET_DIR ?= $(or $(dir $(MAKEFILE_PATH)), $(CURDIR))
# Display the APPFLEET_DIR value
$(info Using APPFLEET_DIR: $(APPFLEET_DIR))
# Validate that APPFLEET_DIR is an existing directory
ifeq ("$(wildcard $(APPFLEET_DIR))","")
    $(error Error: APPFLEET_DIR '$(APPFLEET_DIR)' does not exist or is not accessible.)
endif

REGISTRY-IDS = 991404956194
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

# Use CodeBuild build number if present, otherwise fallback to timestamp for uniqueness
ifdef CODEBUILD_BUILD_NUMBER
  UNIQUE_ID=$(CODEBUILD_BUILD_NUMBER)
  $(info Using CODEBUILD_BUILD_NUMBER: $(CODEBUILD_BUILD_NUMBER))
else
  UNIQUE_ID=$(shell date +%Y%m%d%H%M%S)
  $(info Using UNIQUE_ID generated from timestamp: $(UNIQUE_ID))
endif

$(info UNIQUE_ID="$(UNIQUE_ID)")

# git release version - use for rollbacks
TAG ?= $(BASE_IMAGE_TAG)-$(APPFLEET_RELEASE_NAME)-$(BRANCH_NAME_SAFE)-$(HEAD_VER)-$(UNIQUE_ID)
$(info TAG="$(TAG)")

# Dynamically populate variables based on APPFLEET_BUILD_ARGS
define extract_from_appfleet_details
	$(shell echo '$(APPFLEET_BUILD_ARGS)' | jq -r '.$(1).$(2)')
endef


# Extract keys from APPFLEET_BUILD_ARGS and assign them to IMAGES
IMAGES := $(shell echo '$(APPFLEET_BUILD_ARGS)' | jq -r 'keys[]')

# Debug output to verify the IMAGES variable
$(info IMAGES: $(IMAGES))

$(foreach image,$(IMAGES),$(eval $(image)_REPO := $(call extract_from_appfleet_details,$(image),ecr_repo)))
$(foreach image,$(IMAGES),$(eval $(image)_DOCKERFILE := $(call extract_from_appfleet_details,$(image),dockerfile)))
$(foreach image,$(IMAGES),$(eval $(image)_IMAGE_DETAIL := $(call extract_from_appfleet_details,$(image),image_detail)))
$(foreach image,$(IMAGES),$(eval $(image)_TARGET := $(call extract_from_appfleet_details,$(image),target_arg)))

$(foreach image,$(IMAGES),$(eval $(info $(image) REPO: $($(image)_REPO))))
$(foreach image,$(IMAGES),$(eval $(info $(image) IMAGE DOCKERFILE: $($(image)_DOCKERFILE))))
$(foreach image,$(IMAGES),$(eval $(info $(image) IMAGE DETAIL: $($(image)_IMAGE_DETAIL))))
$(foreach image,$(IMAGES),$(eval $(info $(image) IMAGE TARGET: $($(image)_TARGET))))


default: release

# **Extracts key-value pairs from APPFLEET_DOCKER_BUILD_ARGS as --build-arg**
define extract_build_args
	$(shell echo '$(APPFLEET_DOCKER_BUILD_ARGS)' | jq -r 'to_entries | map("--build-arg \(.key)=\(.value)") | join(" ")')
endef

# **Build Image**
define build_image
	@echo "Running Docker Build command for $(1):"
	$(eval WORKDIR := $(or $(dir $(4)), $(CURDIR)))
	@echo "Using WORKDIR: $(WORKDIR)"
	@if [ ! -d "$(WORKDIR)" ]; then \
	    echo "Error: WORKDIR '$(WORKDIR)' does not exist or is not accessible."; \
	    exit 1; \
	fi

	docker build -t $(2):$(TAG) \
		--platform linux/amd64 \
		$(call extract_build_args) \
		$(if $(strip $(3)),--target $(3)) \
		-f $(4) \
		$(WORKDIR)
	@printf '{"ImageURI":"%s"}' "$(2):$(TAG)" > $(5)
	@echo "Image definitions file created: $(5)"
endef

# **Buildx Image**
define buildx_image
	@echo "Running Docker Buildx command for $(1):"
	$(eval WORKDIR := $(or $(dir $(4)), $(CURDIR)))
	@echo "Using WORKDIR: $(WORKDIR)"
	@if [ ! -d "$(WORKDIR)" ]; then \
	    echo "Error: WORKDIR '$(WORKDIR)' does not exist or is not accessible."; \
	    exit 1; \
	fi

	docker buildx build \
		--platform linux/amd64 \
		$(call extract_build_args) \
		$(if $(strip $(3)),--target $(3)) \
		-f $(4) \
		$(WORKDIR) \
		--cache-from=type=s3,mode=max,region=us-west-2,bucket=$(CACHE_S3_BUCKET),name=$(1),prefix=cache/ \
		--cache-to=type=s3,mode=max,region=us-west-2,bucket=$(CACHE_S3_BUCKET),prefix=cache/ \
		--push \
		-t $(2):$(TAG)
	@printf '{"ImageURI":"%s"}' "$(2):$(TAG)" > $(5)
	@echo "Image definitions file created: $(5)"
endef

# **Push Image**
define push_image
	@echo "Reading image details from $(3)..."
	@IMAGE_URI=$$(jq -r '.ImageURI' $(3)); \
	echo "Pushing Docker image $$IMAGE_URI..."; \
	docker push $$IMAGE_URI
endef

# Build all images
build: $(addprefix build-,$(IMAGES))

buildx: $(addprefix buildx-,$(IMAGES))

build-%:
	$(call build_image,$*,$($*_REPO),$($*_TARGET),$($*_DOCKERFILE),$($*_IMAGE_DETAIL))

buildx-%:
	$(call buildx_image,$*,$($*_REPO),$($*_TARGET),$($*_DOCKERFILE),$($*_IMAGE_DETAIL))

# Push all images
push: $(addprefix push-,$(IMAGES))

push-%:
	$(call push_image,$*,$($*_REPO),$($*_IMAGE_DETAIL))

prebuild:
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 991404956194.dkr.ecr.us-west-2.amazonaws.com
	docker buildx create --use --name mybuilder --driver docker-container

test:
	echo "Reading IMAGE_URI from $(APPFLEET_DIR)/imageDetail.json..."
	IMAGE_URI=$$(jq -r '.ImageURI' $(APPFLEET_DIR)/imageDetail.json); \
	echo "Extracting TAG from IMAGE_URI..."; \
	TAG=$$(echo $$IMAGE_URI | sed 's/.*://'); \
	echo "Testing with TAG: $$TAG"; \
	cd ./tests/basic && IMAGE=$(REPO):$$TAG ./run.sh

deploy:
	echo "Running create-credentials script..."; \
	APPFLEET_DIR=$(APPFLEET_DIR) $(APPFLEET_DIR)/create-credentials.sh; \
	echo "Deploying containers for $(PROJECT_NAME)..."; \
	echo "PROJECT_HANDLE: $(PROJECT_HANDLE)"; \
	echo "APP_NAME: $(APP_NAME)"; \
	echo "APPFLEET_RELEASE_NAME: $(APPFLEET_RELEASE_NAME)"; \
	echo "APPFLEET_TAG_OVERRIDES: $(APPFLEET_TAG_OVERRIDES)"; \
	APPFLEET_RELEASE_NAME=$(APPFLEET_RELEASE_NAME) \
	CONFIG_FILE_URL=$(CONFIG_FILE_URL) \
	APPFLEET_TAG_OVERRIDES="$$APPFLEET_TAG_OVERRIDES" \
	docker-compose -f $(APPFLEET_DIR)/docker-compose.deploy.yaml up --quiet-pull --build --abort-on-container-exit --exit-code-from appfleet-pipeline || exit 1

success:
	@echo "Release complete."

# release: build push
release: buildx
