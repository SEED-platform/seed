#!/bin/bash

# Display the APPFLEET_DIR location
echo "Using APPFLEET_DIR: ${APPFLEET_DIR}"

# Check if APPFLEET_DIR is set and accessible
if [[ -n "${APPFLEET_DIR}" && ! -d "${APPFLEET_DIR}" ]]; then
    echo "Error: APPFLEET_DIR '${APPFLEET_DIR}' does not exist or is not accessible."
    exit 1
fi

# Determine the output directory for AWS files
aws_dir="${APPFLEET_DIR:-.}/.aws"

# Ensure the output directory exists
mkdir -p "${aws_dir}"

# Run the aws configure export-credentials command without the --profile option if AWS_PROFILE is not set
if [[ -z "${AWS_PROFILE}" ]]; then
    export_credentials=$(aws configure export-credentials)
else
    export_credentials=$(aws configure export-credentials --profile "${AWS_PROFILE}")
fi

# Check if export_credentials variable is populated with values
if [[ -z "${export_credentials}" ]]; then
    echo "Error: Unable to retrieve AWS credentials."
    exit 1
fi

# Extract access key ID, secret access key, and session token using jq
access_key_id=$(echo "$export_credentials" | jq -r '.AccessKeyId')
secret_access_key=$(echo "$export_credentials" | jq -r '.SecretAccessKey')
session_token=$(echo "$export_credentials" | jq -r '.SessionToken')

# Check if any of the variables are empty and exit if so
if [[ -z "$access_key_id" || -z "$secret_access_key" || -z "$session_token" ]]; then
    echo "Error: One or more AWS credential variables are empty."
    exit 1
fi

# Write the credentials to the specified credentials file
cat << EOF > "${aws_dir}/credentials"
[default]
aws_access_key_id = $access_key_id
aws_secret_access_key = $secret_access_key
aws_session_token = $session_token
EOF

# Write the default region to the config file in the specified directory
cat << EOF > "${aws_dir}/config"
[default]
region = us-west-2
EOF

echo "AWS credentials file created at ${aws_dir}/credentials"
echo "AWS config file created at ${aws_dir}/config"
