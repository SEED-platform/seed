#!/bin/bash

# Make sure not to echo anything out here becase some of the scripts that test SEED
# call docker-compose run and expect the response to be in the command line.
mkdir -p /seed/collected_static && chmod 775 /seed/collected_static
mkdir -p /seed/media && chmod 777 /seed/media

# set the owner to uwsgi
chown -R uwsgi /seed/collected_static

exec "$@"
