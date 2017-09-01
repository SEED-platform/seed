#!/bin/bash

echo 'Configuring SEED directories and compiling assets'
mkdir -p /seed/collected_static && chmod 775 /seed/collected_static
mkdir -p /seed/media && chmod 777 /seed/media

exec "$@"
