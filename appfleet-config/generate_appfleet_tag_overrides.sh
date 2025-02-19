#!/bin/bash

# Ensure APPFLEET_BUILD_ARGS is set
if [ -z "$APPFLEET_BUILD_ARGS" ]; then
  echo "Error: APPFLEET_BUILD_ARGS is not set."
  exit 1
fi

# Initialize APPFLEET_TAG_OVERRIDES
APPFLEET_TAG_OVERRIDES=""

# Parse the APPFLEET_BUILD_ARGS JSON
for container_name in $(echo "$APPFLEET_BUILD_ARGS" | jq -r 'keys[]'); do
  # Get the path to the ImageDetail.json file
  image_detail_file=$(echo "$APPFLEET_BUILD_ARGS" | jq -r --arg key "$container_name" '.[$key].image_detail')

  # Ensure the file exists
  if [ ! -f "$image_detail_file" ]; then
    echo "Warning: Image detail file '$image_detail_file' for container '$container_name' does not exist. Skipping..."
    continue
  fi

  # Extract the ImageURI from the JSON file
  image_uri=$(jq -r '.ImageURI' "$image_detail_file")

  # Extract the Docker tag from the ImageURI
  docker_tag=${image_uri##*:}

  # Append to APPFLEET_TAG_OVERRIDES
  APPFLEET_TAG_OVERRIDES+=" $container_name:$docker_tag"
done

# Trim leading/trailing whitespace
APPFLEET_TAG_OVERRIDES=$(echo "$APPFLEET_TAG_OVERRIDES" | xargs)

# Export the APPFLEET_TAG_OVERRIDES variable
export APPFLEET_TAG_OVERRIDES

# Output var
echo "$APPFLEET_TAG_OVERRIDES"
